
import math
import requests
import os

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv


app = Flask(__name__)

load_dotenv()


# API endpoints
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")


# Application configuration
SEARCH_RADIUS = 5000  # 5km
REQUEST_TIMEOUT = 30


# Identify our application when using Nominatim
HEADERS = {
    "User-Agent": "FlavourQuest/1.0 (restaurant discovery application)"
}


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two geographical coordinates in km."""

    earth_radius = 6371

    lat1, lon1, lat2, lon2 = map(
        math.radians, [lat1, lon1, lat2, lon2]
    )

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius * c


def get_coordinates(location):
    """Convert a typed location into geographical coordinates."""

    parameters = {
        "q": location,
        "format": "jsonv2",
        "limit": 1
    }

    response = requests.get(
        NOMINATIM_URL,
        params=parameters,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    results = response.json()

    if not results:
        return None

    return {
        "latitude": float(results[0]["lat"]),
        "longitude": float(results[0]["lon"])
    }


def get_address_from_coordinates(latitude, longitude):
    """Convert geographical coordinates into a readable address."""

    parameters = {
        "lat": latitude,
        "lon": longitude,
        "format": "jsonv2"
    }

    response = requests.get(
        NOMINATIM_REVERSE_URL,
        params=parameters,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    data = response.json()

    return data.get("display_name")


def get_restaurants(latitude, longitude, radius=SEARCH_RADIUS):
    """Retrieve nearby restaurants using the Geoapify Places API."""

    if not GEOAPIFY_API_KEY:
        raise RuntimeError("Geoapify API key is not configured.")

    geoapify_url = "https://api.geoapify.com/v2/places"

    parameters = {
        "categories": "catering.restaurant",
        "filter": f"circle:{longitude},{latitude},{radius}",
        "limit": 20,
        "apiKey": GEOAPIFY_API_KEY
    }

    response = requests.get(
        geoapify_url,
        params=parameters,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    data = response.json()

    restaurants = []

    for feature in data.get("features", []):

        properties = feature.get("properties", {})

        raw_data = (
            properties.get("datasource", {})
            .get("raw", {})
        )

        # GeoJSON coordinates are ordered as longitude, latitude
        geometry = feature.get("geometry", {})
        coordinates = geometry.get("coordinates", [])

        if len(coordinates) < 2:
            continue

        restaurant_lon = float(coordinates[0])
        restaurant_lat = float(coordinates[1])

        address = properties.get(
            "formatted",
            "Address not available"
        )

        restaurant_distance = calculate_distance(
            latitude,
            longitude,
            restaurant_lat,
            restaurant_lon
        )

        restaurant = {
            "name": properties.get(
                "name",
                "Unnamed Restaurant"
            ),
            "cuisine": raw_data.get(
                "cuisine",
                "Not specified"
            ),
            "address": address,
            "phone": raw_data.get("phone", ""),
            "website": raw_data.get("website", ""),
            "opening_hours": raw_data.get("opening_hours", ""),
            "rating": None,
            "review_count": None,

            "location": {
                "address1": properties.get("address_line1", ""),
                "city": properties.get("city", ""),
                "state": properties.get("state", ""),
                "zip_code": properties.get("postcode", "")
            },

            "coordinates": {
                "latitude": restaurant_lat,
                "longitude": restaurant_lon
            },

            "distance": round(restaurant_distance, 2),

            "categories": properties.get("categories", []),
            "place_id": properties.get("place_id", "")
        }

        restaurants.append(restaurant)

    # Sort restaurants by nearest distance
    restaurants.sort(key=lambda item: item["distance"])

    return restaurants


# Current-location reverse geocoding endpoint
@app.route("/reverse-geocode", methods=["POST"])
def reverse_geocode():

    data = request.get_json(silent=True) or {}

    try:
        latitude = float(data.get("latitude"))
        longitude = float(data.get("longitude"))

        # Validate geographical coordinates
        if not (
            math.isfinite(latitude)
            and math.isfinite(longitude)
            and -90 <= latitude <= 90
            and -180 <= longitude <= 180
        ):
            return jsonify({
                "error": "Invalid location coordinates."
            }), 400

        address = get_address_from_coordinates(
            latitude,
            longitude
        )

        if not address:
            return jsonify({
                "error": "Unable to find an address for your location."
            }), 404

        return jsonify({
            "address": address,
            "latitude": latitude,
            "longitude": longitude
        })

    except requests.exceptions.Timeout:
        return jsonify({
            "error": "The location service took too long to respond."
        }), 504

    except requests.exceptions.RequestException:
        return jsonify({
            "error": "Unable to connect to the location service."
        }), 502

    except (TypeError, ValueError):
        return jsonify({
            "error": "Invalid location coordinates."
        }), 400


# Main application route
@app.route("/", methods=["GET", "POST"])
def fetching_data():

    if request.method == "POST":

        # Get submitted location and coordinates
        location = request.form.get("location", "").strip()

        latitude_value = request.form.get(
            "latitude", ""
        ).strip()

        longitude_value = request.form.get(
            "longitude", ""
        ).strip()

        # Allow either a typed location or current coordinates
        if not location and not (
            latitude_value and longitude_value
        ):
            return render_template(
                "index.html",
                error="Please enter a location or use your current location."
            )

        # Get and validate the selected search radius
        selected_radius = request.form.get(
            "radius", str(SEARCH_RADIUS)
        )

        try:
            selected_radius = int(selected_radius)

        except ValueError:
            return render_template(
                "index.html",
                error="Please select a valid search radius."
            )

        # Only allow these three radius options
        allowed_radii = {1000, 3000, 5000}

        if selected_radius not in allowed_radii:
            return render_template(
                "index.html",
                error="Please select a valid search radius."
            )

        try:

            # Step 1: Get coordinates from current location or typed address

            if latitude_value or longitude_value:

                # Use coordinates supplied by the browser
                try:
                    latitude = float(latitude_value)
                    longitude = float(longitude_value)

                    if not (
                        math.isfinite(latitude)
                        and math.isfinite(longitude)
                        and -90 <= latitude <= 90
                        and -180 <= longitude <= 180
                    ):
                        raise ValueError("Invalid coordinates")

                except (TypeError, ValueError):
                    return render_template(
                        "index.html",
                        error="Invalid current location. Please try again."
                    )

            else:

                # Use the existing manual location search
                coordinates = get_coordinates(location)

                if coordinates is None:
                    return render_template(
                        "index.html",
                        error="Location not found. Please try another location."
                    )

                latitude = coordinates["latitude"]
                longitude = coordinates["longitude"]

            # Step 2: Retrieve restaurants within selected radius
            restaurants = get_restaurants(
                latitude,
                longitude,
                selected_radius
            )

            # Step 3: Display restaurant results
            return render_template(
                "restaurants.html",
                restaurants=restaurants,
                searched_location=location or "Your current location",
                search_radius=selected_radius / 1000
            )

        except requests.exceptions.Timeout:
            error_message = "The location service took too long to respond."

        except requests.exceptions.HTTPError:
            error_message = "A location or restaurant service returned an error."

        except requests.exceptions.RequestException:
            error_message = "Unable to connect to the location services."

        except (ValueError, KeyError, TypeError, IndexError):
            error_message = "Received unexpected data from a location service."

        except RuntimeError:
            error_message = "Application configuration error. Please check the API settings."

        return render_template(
            "index.html",
            error=error_message
        )

    return render_template("index.html")

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)