import sys
sys.dont_write_bytecode = True
import time
import requests
import json
from json import JSONDecodeError
from urllib.parse import urlencode
import re
import datetime
import random
import os
import logging
import logging.handlers
from scheduledtask import scheduledtask


'''
:rand:
        total_hits = json_data["categoryTotals"]["cat1"]["totalResultCount"]
        #r3 = re.findall(r'(\\"responsivePhotos\\":\[[^\s]+\]),*', response.text)[0]
        #ans = r3.replace("\\","")
        #print(str(ans))


        #print(new_listing["detailUrl"].split("-"+new_listing["city"].replace(" ","-")+"-"))
        #address = new_listing["detailUrl"].split(self.ADDRESS_REGEX.format(new_listing["city"].replace(" ","-"))))
        ADDRESS_REGEX = "/homedetails/([^\s]+)-{}-[A-Z]{2}-[0-9]{5}/"
        

'''

def create_logger():

    global logger
    log_dir = "logging/"
    log_file = log_dir + "Zillow_log"
    
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    
    if not os.path.isfile(log_file):
        open(log_file, 'a')

    logger = logging.getLogger("Zillow_log")
    logger.setLevel(level=logging.INFO)
    log_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=1)
    log_handler.setFormatter(logging.Formatter("%(levelname)s (%(processName)-10s) (%(threadName)-10s) %(asctime)s " +
                                               "[%(name)s:%(lineno)s] %(message)s"))
    logger.addHandler(log_handler)


class ZillowParser:

    REQUEST_HEADERS = {
            "accept-language": "en-US,en;q=0.9",
            "user-agent": "Mozilla/3.0 (Macintosh; Intel Mac OS X 9_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "accept-language": "en-US;en;q=0.9",
            "accept-encoding": "gzip, deflate, br",
            "authority": "www.zillow.com",
            "cache-control": "max-age=0",
            "sec-fetch-site": "same-origin"
        }
    
    ADDRESS_REGEX_FH = '/homedetails/((?:[^\s]+))-'
    ADDRESS_REGEX_BH = '-[A-Z]{2}-[0-9]{5}/'
    URL_PREFIX = "https://www.zillow.com"
    GEOLOCATION_URL = URL_PREFIX + "/homes/{},-{}_rb"
    BULK_LISTINGS_URL = URL_PREFIX + "/search/GetSearchPageState.htm?"

    SQUARE_FEET_REGEX= "Living area range<!-- -->: <!-- -->(\d{3,6}\s-\s\d{3,6}) Square Feet<"
    BUILD_YEAR_REGEX= "Year built<!-- -->: <!-- -->(\d{4})<"
    LISTING_AGENTS_REGEX= r'\\\"agentName\\\":\\\"([^\\\"]+)\\\"'

    FIELDS = ("price", "latitude", "longitude", "price", "beds", "city", "state", "zipcode", "baths", "zipcode", "homeType", "detailUrl", "streetAddress", "pgapt", "lotAreaValue")
    
    def __init__(self):
        self.zillow_session = None
        self.city = None
        self.state = None
        self.filters = None
        self.listing_attributes = []
        self.geo_bounds = None
        self.sleep_interval = 60 * 30
        self.purge_listings_interval = 60 * 24
        self.listings = {"listings": {}, "timestamp": "None", "listingsCount": 0}
        self.directory_path = "data/"

        create_logger()


    def init_zillow_parser(self, city, state, directory_path=None, filters=None, listing_attributes=None):
        self.city = city
        self.state = state

        if filters:
            self.filters = filters
            
        if listing_attributes:
            self.listing_attributes = listing_attributes

        if directory_path:
            self.directory_path = directory_path

        self.zillow_session = requests.session()
        self.geo_bounds = self.init_geo_bounds()
        

    def init_geo_bounds(self):
        geo_bounds = None

        response = self.zillow_session.get(self.GEOLOCATION_URL.format(self.city, self.state) ,headers=self.REQUEST_HEADERS)

        geo_location_regex = re.findall(r"<!--({.+})-->", response.text)

        if len(geo_location_regex) > 0:
            geo_bounds = json.loads(geo_location_regex[0])["queryState"]["mapBounds"]
        
        return geo_bounds


    def parse_all_listings(self, parameters):
        data = None
        try:
            response = self.zillow_session.get(self.BULK_LISTINGS_URL + urlencode(parameters), headers=self.REQUEST_HEADERS)
            if response.text:
                data = json.loads(response.text)["cat1"]["searchResults"]["mapResults"]
                del response

            return data

        except JSONDecodeError as e:
            logger.error("parse_all_listings()======> Bad JSON value: {}".format(e.msg))
            logger.error("parse_all_listings()======> EXCEPTION: {}".format(response.text))

            return data

    def construct_address_regex(self, listing_city):
        city = listing_city.replace(" ","-")
        return self.ADDRESS_REGEX_FH + city + self.ADDRESS_REGEX_BH


    def get_additional_info(self, listing):
        listing_details = self.zillow_session.get(listing["detailUrl"], headers=self.REQUEST_HEADERS)

        sq_ft = re.findall(ZillowParser.SQUARE_FEET_REGEX, listing_details.text)
        if sq_ft:
            listing["squarefeet"]= sq_ft[0]
            logger.info("Square Feet: {}".format(sq_ft[0]))
        
        year_built = re.findall(ZillowParser.BUILD_YEAR_REGEX, listing_details.text)
        if year_built:
            listing["buildyear"]= year_built[0]
            logger.info("Build Year: {}".format(year_built[0]))

        agents = re.findall(ZillowParser.LISTING_AGENTS_REGEX, listing_details.text)
        logger.info(len(agents))
        if agents:
            listing["agents"]= agents
            logger.info("Agents: {}".format(agents))

    def parse_address(self, listing):
        try:
            address_regex = self.construct_address_regex(listing["city"])
            address = re.findall(address_regex, listing["detailUrl"])

            if address and len(address) == 1:
                listing["address"] = address[0]
                return listing["address"]
            
        except Exception as e:
            logger.error(e.with_traceback)
        return None
    
    def get_listing_directory(self, listing):
        return "{}/{}/{}".format(listing['state'], listing['city'].replace(" ","-"), listing["address"])

    def validate_listing(self, listing):
        result = [attrib for attrib in ["city", "state", "price"] if attrib not in listing or listing[attrib] == ""]
        return len(result) == 0, result

    def get_listings(self, get_images=False, num_images=5):
        parameters = {
            "searchQueryState": {
                "usersSearchTerm": self.city + "," + self.state,
                "mapBounds": self.geo_bounds,
                "filterState": {
                    "price": {
                        "max": 350000,
                        "min": None
                    },
                    "isAllHomes":{
                        "value": True
                    },
                    "isCondo":{
                        "value": False
                    },
                    "isMultiFamily":{
                        "value": False
                    },
                    "isManufactured":{
                        "value": False
                    },
                    "isLotLand":{
                        "value": False
                    },
                    "isTownhouse":{
                        "value": False
                    },
                    "isApartment":{
                        "value": False
                    },
                    "isApartmentOrCondo":{
                        "value": False
                    },
                    "beds": {
                        "min": 3,
                        "max": None
                    },
                    "baths": {
                        "min": 2,
                        "max": None
                    },
                    "doz":{
                        "value": None
                    }
                }
            },
            "wants": {
                "cat1": ["mapResults", "listResults"],
                "cat2":[]
            },
            "requestId": random.randint(0,10)
        }
        
        listings = {
            "listings": {},
            "timestamp": None,
            "listingsCount": 0
        }

        all_listings = self.parse_all_listings(parameters)

        if not all_listings:
            logger.error("get_listings()======> Failed to get all_listings.....")
            return

        logger.info("get_listings()======> ")
        logger.info("get_listings()======> Got {} listings".format(len(all_listings)))

        for i in range(len(all_listings)):

            new_listing = self.create_listing(all_listings[i])

            valid_listing, missing_attributes = self.validate_listing(new_listing)
            
            if not valid_listing:
                logger.warning("get_listings()======> Failed to create listing ({}/{}) {} because required attributes were not found {}".format(i, len(all_listings), new_listing, missing_attributes))
                continue
            
            address = self.parse_address(new_listing)

            if not address:
                logger.warning("get_listings()======> Failed to create listing ({}/{}) {} because no address was found".format(i, len(all_listings), new_listing))
                continue

            self.get_additional_info(new_listing)

            listings["listings"][address] = new_listing
            
            if not get_images:
                logger.info("get_listings()======> Added listing ({}/{}) {}".format(i, len(all_listings), address))
                time.sleep(.5)
                continue
            
            listing_response = self.zillow_session.get(new_listing["detailUrl"], headers=self.REQUEST_HEADERS)
            
            images_regex = re.findall(r'\"url\":\"([^\s,]+\.jpg)\",*\"width\":576', listing_response.text.replace("\\",""))

            listing_directory = self.get_listing_directory(new_listing)
            
            max_images = min(len(images_regex), num_images)

            if not os.path.exists(listing_directory):
                os.makedirs(listing_directory)
            else:
                continue

            for j in range(max_images):
                image = self.zillow_session.get(images_regex[j], headers=self.REQUEST_HEADERS)
                image_data = image.content
                image_file_name = listing_directory + "/" + str(j) + ".jpg"

                with open(image_file_name, 'wb') as image_writer:
                    image_writer.write(image_data)
            
            logger.info("get_listings()======> Added listing ({}/{}) {} and retreived {} images".format(i, len(all_listings), address, max_images))

        listings['timestamp'] = datetime.datetime.now().strftime("%m-%d-%Y-%I_%M-{}-{}".format(self.city, self.state))
        listings['listingsCount'] = len(listings['listings'])
        
        logger.info("get_listings()======> Successfully finished creating {} listings".format(len(listings["listings"])))
        logger.info("get_listings()======> Failed to add {} listings".format(len(all_listings) - len(listings["listings"])))

        self.listings = listings
        return listings

    def flatten_dict(self, dict_obj, listing_obj, atribs):
        for atrib in dict_obj:
            if isinstance(dict_obj[atrib], dict):
                if atrib == "latLong":
                    #listing_obj["loc"] = {}
                    #listing_obj["loc"]["lat"] = dict_obj[atrib]["latitude"]
                    #listing_obj["loc"]["lon"] = dict_obj[atrib]["longitude"]
                    listing_obj[atrib] = dict_obj[atrib]
                    continue
                self.flatten_dict(dict_obj[atrib], listing_obj, atribs)
            else:
                if atrib in atribs:
                    if atrib == "detailUrl":
                        dict_obj[atrib] = self.URL_PREFIX + dict_obj[atrib]
                    if atrib == "price":
                        dict_obj[atrib] = str(dict_obj[atrib]).replace("From ", "")

                    listing_obj[atrib] = dict_obj[atrib]

    def create_listing(self, listing_json):
        new_listing = {}
        self.flatten_dict(listing_json, new_listing, ZillowParser.FIELDS)

        return new_listing

    def load_previous_listings(self):
        logger.info(os.listdir("data"))

    def get_file_name(self):
        return str(self.directory_path + self.listings["timestamp"] + ".json")

if __name__ == "__main__":
    zp = ZillowParser()
    zp.init_zillow_parser("Greensboro", "NC")
    logger.info("main()======> Zillow Parser has started running...")


    def hello():
        logger.info("hello, world")
    #t = scheduledtask(10, hello)
    #t.start()
    while True:
        if not os.path.exists(zp.directory_path):
            # initial entrypoint for first call 
            logger.info("creating dir data")
            os.makedirs(zp.directory_path)
            
            if zp.get_listings(num_images=5):
                logger.info("got listings sleeping for 1 hour")
                with open(zp.get_file_name(), 'w') as handler:
                    handler.write(json.dumps(zp.listings, indent=4))
            else:
                logger.info("couldn't get any listings")
            time.sleep(zp.sleep_interval)
            continue
        

        else:
            # 1. get most recent .json from dir and read into old_listings
            # 2. call get listings and put into new_listings
            # 3. do stuff, then write new listings to new file

            #or

            # load old_listing.json
            # delete old_listing.json
            # get new listings
            # compare old and new listings
            # rewrite new listings.json
            if zp.get_listings(num_images=5):
                logger.info("got listings sleeping for 1 hour")
                with open(zp.get_file_name(), 'w') as handler:
                    handler.write(json.dumps(zp.listings, indent=4))
            else:
                logger.info("couldn't get any listings")
            time.sleep(zp.sleep_interval)

