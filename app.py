import os
import config
import json
import random
from yelpapi import YelpAPI
from geopy.geocoders import Nominatim
from flask import Flask, render_template 
from flask.ext.wtf import Form
from wtforms import IntegerField, DecimalField, SubmitField
from wtforms.validators import Required, NumberRange
from flask.ext.script import Manager, Shell, Server
from time import time
from uber_rides.session import Session
from uber_rides.client import UberRidesClient



# Config

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = config.SECRET_KEY

manager = Manager(app)

def make_shell_context():
    return dict(app=app)
manager.add_command("shell", Shell(make_context=make_shell_context))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

yelp_api = YelpAPI(config.YELP_CONSUMER_KEY, config.YELP_CONSUMER_SECRET, 
                   config.YELP_TOKEN, config.YELP_TOKEN_SECRET)

uber_session = Session(server_token=config.UBER_SERVER_TOKEN)
uber_client = UberRidesClient(uber_session)

geolocator = Nominatim()

categories = 'amusementparks,aquariums,beaches,bowling,escapegames,gokarts,'\
             'hiking,lakes,parks,skatingrinks,skydiving,zoos,arcades,gardens,'\
             'movietheaters,festivals,jazzandblues,museums,musicvenues,'\
             'observatories,opera,planetarium,psychic_astrology,bars,'\
             'comedyclubs,danceclubs,karaoke,poolhalls,fleamarkets,food'



# Forms

class RequestForm(Form):
    amount = IntegerField(
        'Amount', 
        validators=[
            Required(message="Choose a number from 1 to 50"), 
            NumberRange(min=1, max=50, message="Choose a number from 1 to 50"),
        ], 
        default=7,
    )
    latitude = DecimalField('Latitude', validators=[Required()])
    longitude = DecimalField('Longitude', validators=[Required()])
    submit = SubmitField('Go')



# Helpers

def construct_deep_link(chosen_lat, chosen_long, chosen_name, 
                        chosen_address, uber_product_id):
    return "uber://?client_id=" + config.UBER_CLIENT_ID +\
           "&action=setPickup" +\
           "&pickup=my_location" +\
           "&dropoff[latitude]=" + str(chosen_lat) +\
           "&dropoff[longitude]=" + str(chosen_long) +\
           "&dropoff[nickname]=" + chosen_name +\
           "&dropoff[formatted_address]=" + chosen_address +\
           "&product_id=" + uber_product_id


def find_chosen_one(destinations, travel_money, 
                    start_lat, start_long, uber_index):
    i = 0
    while (i < len(destinations)) and (destinations[i]['rating'] > 3.5):
        i += 1
    destinations = destinations[:i]
    high_estimate = travel_money + 1
    destinations.append(None)
    chosen = None
    while high_estimate > travel_money:
        destinations.remove(chosen)
        if len(destinations) > 0:
            chosen = random.choice(destinations)
        else:
            return render_template('womp.html')
        chosen_lat = chosen['location']['coordinate']['latitude']
        chosen_long = chosen['location']['coordinate']['longitude']
        uber_price_estimate = uber_client.get_price_estimates(
            start_latitude=start_lat,
            start_longitude=start_long,
            end_latitude=chosen_lat,
            end_longitude=chosen_long,
            seat_count=1).json.get('prices')
        uber_price = uber_price_estimate[uber_index]
        product_id = uber_price['product_id']
        high_estimate = uber_price['high_estimate']
    print("picked " + chosen['name'])
    return chosen, chosen_lat, chosen_long, uber_price


def retrieve_uber_product(start_lat, start_long):
    uber_products_response = uber_client.get_products(start_lat, start_long)
    uber_products = uber_products_response.json.get('products')
    for i in xrange(len(uber_products)):
        display_name = uber_products[i]['display_name']
        if display_name == 'uberX':
            uber_index = i
            break
    uber_product_id = uber_products[uber_index]['product_id'] 
    uber_product_response = uber_client.get_product(uber_product_id)
    uber_price_details = uber_product_response.json['price_details']
    print("retrieved uber product and price details")
    return uber_product_id, uber_price_details, uber_index


def determine_travel_funds(uber_price_details, amount):
    uber_service_fees = 0
    for fee in uber_price_details['service_fees']:
        uber_service_fees += fee['fee']
    print("determined remaining travel funds")
    return amount - uber_price_details['base'] - uber_service_fees


def grab_yelps(travel_funds, uber_price_details, start_lat, start_long):
    radius_meters = travel_funds / (uber_price_details['cost_per_distance']
                    + uber_price_details['cost_per_minute'] * 3) * 1609
    start_coords = str(start_lat) + ', ' + str(start_long)
    town = str(geolocator.reverse(start_coords).raw['address']['city'])
    print("found " + town)
    yelp_data = yelp_api.search_query(location=town, sort=2,
        category_filter=categories, radius_filter=radius_meters,
        cll=start_coords, limit=20)
    print("grabbed yelp results")
    return yelp_data['businesses']



# Routes

@app.route('/', methods=['GET', 'POST'])
def index():
    form = RequestForm()
    if form.validate_on_submit():
        amount = form.amount.data
        start_lat = form.latitude.data
        start_long = form.longitude.data
        
        try:
            uber_product_id, uber_price_details, uber_index =\
                retrieve_uber_product(start_lat, start_long)
            travel_funds = determine_travel_funds(uber_price_details, amount)
            destinations = grab_yelps(travel_funds, uber_price_details, 
                start_lat, start_long) 
            chosen, chosen_lat, chosen_long, uber_price = find_chosen_one(
                destinations, travel_funds, start_lat, start_long, uber_index)
            chosen_name = chosen['name'].replace(' ', '%20')
            display_address = ' '.join(chosen['location']['display_address'])
            chosen_address = display_address.replace(' ', '%20')
            deep_link = construct_deep_link(chosen_lat, chosen_long, 
                chosen_name, chosen_address, uber_product_id)
            return render_template('boom.html', deep_link=deep_link, 
                d_name=chosen['name'], d_address=display_address,
                d_cost=uber_price['estimate'], d_rating=chosen['rating'],
                d_url=chosen['mobile_url'],
                d_product=uber_price['display_name'])
        except:
            return render_template('womp.html')
    else:
        return render_template('index.html', form=form)
        


if __name__ == '__main__':
    manager.run()
  
    
