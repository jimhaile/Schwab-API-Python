from dotenv import load_dotenv
import schwabdev
import os
from schwabdev import api, Client


# place your app key and app secret in the .env file
load_dotenv()  # load environment variables from .env file

client = schwabdev.Client(os.getenv('app_key'), os.getenv('app_secret'), os.getenv('callback_url'))
client._update_refresh_token()