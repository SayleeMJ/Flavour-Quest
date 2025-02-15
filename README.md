# Flavour Quest

A web application that helps users discover restaurants based on their desired location.

## Features

* Search for restaurants by location.
* View restaurant details, including ratings, reviews, and addresses.
* See restaurant locations on a map.

## Technologies Used

* Flask
* Yelp API
* Google Maps API

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/SayleeMJ/Flavour-Quest.git
   ```

2. Install the dependencies:
   ```bash
    pip install -r requirements.txt
   ```
3. Set the FLASK_APP environment variable:
   ```bash
   set FLASK_APP=app.py
   ```
4. Obtain API keys for Yelp and Google Maps and replace the placeholders in app.py.

## Usage
1. Run the application:
   ```bash
   flask run
   ```
2. Open your web browser and go to http://127.0.0.1:5000/.
3. Enter a location in the search bar and click "Search".
4. View the list of recommended restaurants.
