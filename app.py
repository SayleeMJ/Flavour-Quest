import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Loading API keys from environment variables
yelpApiKey = 'KaDrWocoz1o7PJTFUqLOTCcmxGbDxCde1j93TBTLU5oWqi3-YgkDeWXJzJUlbNcugjGW_KSFR9W8iHMD3OFC1vG2yTEoi8bhapzh391cCvNdfno1ty809gXlGSmKZHYx'
googleMapsApiKey = 'AIzaSyDzQYs_ynQ18mfGnIk2n75C7GJRCOz6B5Q'

# Defining API endpoints for fetching data
yelpApiEndpoint = 'https://api.yelp.com/v3/businesses/search'
googleMapsEndpoint = 'https://maps.googleapis.com/maps/api/geocode/json'


# Function for handling the root URL '/' route in this application
# Handles GET and POST requests
@app.route('/', methods=['GET', 'POST'])
def fetching_data():
    # To receive the values from form
    if request.method == 'POST':
        location = request.form['location']

        # Geocode location parameters using Google Maps API
        geocode_parameters = {
            'address': location,
            'key': googleMapsApiKey
        }
        geocode_responses = requests.get(googleMapsEndpoint, params=geocode_parameters)
        geocode_data = geocode_responses.json()
        try:
            if geocode_data['status'] == 'OK':
                # Getting coordinates from geocoding responses
                coordinates = geocode_data['results'][0]['geometry']['location']
                lat = coordinates['lat']
                lng = coordinates['lng']

                # Making request to Yelp using google coordinates and search cuisine
                headers = {
                    'Authorization': f'Bearer {yelpApiKey}'
                }

                # Setting parameters for yelp api with search limit 20 for result
                yelp_parameters = {
                    'latitude': lat,
                    'longitude': lng,
                    'location': location,
                    'limit': 20
                }
                yelp_responses = requests.get(yelpApiEndpoint, headers=headers, params=yelp_parameters)
                yelp_data = yelp_responses.json()

                # Extracting list of restaurants from yelp responses
                list_of_restaurants = yelp_data.get('businesses', [])

                return render_template('restaurants.html', restaurants=list_of_restaurants)
            else:
                # Handling error incase geocoding fails
                error_messages = "Geocoding failed. Please try again."
                return render_template('index.html', error=error_messages)
        except requests.exceptions.RequestException:
            # Handling error if there is an issue with making API requests
            error_messages = "Error occurred while making API requests. Please try again."
            return render_template('index.html', error=error_messages)
    return render_template('index.html')

# Start of the code
if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)
