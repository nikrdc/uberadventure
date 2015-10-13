import os
import config
import requests
import json
import random
from yelpapi import YelpAPI
from nominatim import NominatimReverse
from flask import Flask, render_template 
from flask.ext.wtf import Form
from wtforms import IntegerField, DecimalField, SubmitField
from wtforms.validators import Required, NumberRange
from flask.ext.script import Manager, Shell, Server



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

yelp_api = YelpAPI(config.YELP_CONSUMER_KEY, config.YELP_CONSUMER_SECRET, 
				   config.YELP_TOKEN, config.YELP_TOKEN_SECRET)

nomrev = NominatimReverse()

categories = 'amusementparks,aquariums,beaches,bowling,escapegames,gokarts,'+\
			 'hiking,lakes,parks,skatingrinks,skydiving,zoos,arcades,'+\
			 'gardens,movietheaters,festivals,jazzandblues,museums,'+\
			 'musicvenues,observatories,opera,planetarium,psychic_astrology,'+\
			 'bars,comedyclubs,danceclubs,karaoke,poolhalls,fleamarkets'



# Forms

class RequestForm(Form):
    amount = IntegerField('Amount', validators=[
    	Required(message="Choose a number from 0 to 50"), 
    	NumberRange(min=1, max=50, message="Choose a number from 0 to 50"),], 
    	default=7,)
    latitude = DecimalField('Latitude', validators=[Required()])
    longitude = DecimalField('Longitude', validators=[Required()])
    submit = SubmitField('Go')



# Routes

@app.route('/', methods=['GET', 'POST'])
def index():
	form = RequestForm()
	if form.validate_on_submit():
		amount = form.amount.data
		start_lat = form.latitude.data
		start_lon = form.longitude.data
		product_url = 'https://api.uber.com/v1/products'
		product_parameters = {
		    'server_token': config.UBER_SERVER_TOKEN,
		    'latitude': start_lat,
		    'longitude': start_lon,
		}
		product_response = requests.get(product_url, params=product_parameters)
		product_data = product_response.json()
		price_details = product_data['products'][0]['price_details']
		service_fees = 0
		for fee in price_details['service_fees']:
			service_fees += fee['fee']
		travel_money = amount - price_details['base'] - service_fees
		radius_miles = travel_money / (price_details['cost_per_distance'] + 
								 	   price_details['cost_per_minute'] * 3)
		radius_meters = radius_miles * 1609
		latlong=str(start_lat)+', '+str(start_lon)
		town = str(nomrev.query(lat=start_lat, 
								lon=start_lon)['address']['city'])
		yelp_data = yelp_api.search_query(location=town, 
										  sort=2,
										  category_filter=categories,
										  radius_filter=radius_meters,
							  			  cll=latlong,
							  			  limit=20,)
		yelp_data2 = yelp_api.search_query(location=town, 
										   sort=2,
										   category_filter=categories,
										   radius_filter=radius_meters,
							  			   cll=latlong,
							  			   limit=20,
							  			   offset=20,)
		destinations = yelp_data['businesses'] + yelp_data2['businesses']
		if len(destinations) == 0:
			return render_template('womp.html')
		i = 0
		while (i < len(destinations)) and (destinations[i]['rating'] > 3.5):
			i += 1
		destinations = destinations[:i]
		high_estimate = amount + 1
		destinations.append(None)
		chosen = None
		while high_estimate > amount:
			destinations.remove(chosen)
			if destinations:
				chosen = random.choice(destinations)
			else:
				return render_template('womp.html')
			price_url = 'https://api.uber.com/v1/estimates/price'
			chosen_lat = chosen['location']['coordinate']['latitude']
			chosen_lon = chosen['location']['coordinate']['longitude']
			price_parameters = {
				'server_token': config.UBER_SERVER_TOKEN,
				'start_latitude': start_lat,
				'start_longitude': start_lon,
				'end_latitude': chosen_lat,
				'end_longitude': chosen_lon,
			}
			price_response = requests.get(price_url, params=price_parameters)
			price_data = price_response.json()
			product_id = price_data['prices'][0]['product_id']
			high_estimate = price_data['prices'][0]['high_estimate']
		chosen_name = chosen['name'].replace(' ', '%20')
		d_address = ' '.join(chosen['location']['display_address'])
		chosen_address = '%20'.join(chosen['location']['display_address']).replace(' ','%20')
		deep_link = "uber://?client_id="+config.UBER_CLIENT_ID+\
					"&action=setPickup&pickup=my_location&dropoff[latitude]="+\
					str(chosen_lat)+"&dropoff[longitude]="+str(chosen_lon)+\
					"&dropoff[nickname]="+chosen_name+\
					"&dropoff[formatted_address]="+chosen_address+\
					"&product_id="+product_id
		return render_template('boom.html', 
							   deep_link=deep_link, 
							   d_name=chosen['name'], 
							   d_address=d_address,
							   d_cost=price_data['prices'][0]['estimate'], 
							   d_rating=chosen['rating'],
							   d_url=chosen['mobile_url'],
							   d_product=price_data['prices'][0]['display_name'],)
	else:
		return render_template('index.html', form=form)
		


if __name__ == '__main__':
    manager.run()
	
    
