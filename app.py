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
from wtforms.validators import Required
from flask.ext.script import Manager, Shell, Server



# Config

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = config.SECRET_KEY

manager = Manager(app)

def make_shell_context():
    return dict(app=app)
manager.add_command("shell", Shell(make_context=make_shell_context))

yelp_api = YelpAPI(config.YELP_CONSUMER_KEY, config.YELP_CONSUMER_SECRET, 
				   config.YELP_TOKEN, config.YELP_TOKEN_SECRET)

nomrev = NominatimReverse()

categories = 'amusementparks,aquariums,beaches,bowling,escapegames,gokarts,'+\
			 'hiking,lakes,parks,skatingrinks,skydiving,zoos,arcades,'+\
			 'galleries,gardens,movietheaters,festivals,jazzandblues,'+\
			 'museums,musicvenues,observatories,opera,theater,planetarium,'+\
			 'psychic_astrology'



# Forms

class RequestForm(Form):
    amount = IntegerField('Amount', validators=[Required()])
    latitude = DecimalField('Latitude', validators=[Required()])
    longitude = DecimalField('Longitude', validators=[Required()])
    submit = SubmitField('Go')



# Routes

@app.route('/')
def index():
	form = RequestForm()
	if form.validate_on_submit():
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
		json.loads(product_data)
		price_details = product_data['products'][0]['price_details']
		service_fees = 0
		for fee in price_details['service_fees']:
			service_fees += fee['fee']
		travel_money = form.amount.data - price_details['base'] - service_fees
		radius_miles = travel_money / (price_details['cost_per_distance'] + 
								 	   price_details['cost_per_minute'] * 3)
		radius_meters = radius_miles * 1609
		latlong=start_lat+', '+start_lon
		town = str(nomrev.query(lat=start_lat, 
								lon=start_lon)['address']['city'])
		yelp_data = yelp_api.search_query(location=town, 
										  sort=2,
										  category_filter=categories,
										  radius_filter=radius_meters,
							  			  cll=latlong)
		destinations = yelp_data['businesses']
		i = 0
		while destinations[i]['rating'] > 4:
			i += 1
		destinations = destinations[:i]
		high_estimate = 11
		destinations.append(None)
		chosen = None
		while high_estimate > 10:
			destinations.remove(chosen)
			if destinations:
				chosen = random.choice(destinations)
			else:
				return render_template('boom.html', found=False, chosen=None)
			price_url = 'https://api.uber.com/v1/estimates/price'
			price_parameters = {
				'server_token': '0tGY3guCZLpjknxJgwzwCAx8YBxPC0eN2hWCb4io',
				'start_latitude': '37.870596024328044',
				'start_longitude': '-122.25148560974111',
				'end_latitude': chosen['location']['coordinate']['latitude'],
				'end_longitude': chosen['location']['coordinate']['longitude']
			}
			price_response = requests.get(price_url, params=price_parameters)
			price_data = price_response.json()
			high_estimate = price_data['prices'][0]['high_estimate']
		return render_template('boom.html', found=True, chosen=chosen)
	else:
		return render_template('index.html', form=form)
		


if __name__ == '__main__':
    manager.run()
	
    
