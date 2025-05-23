import schwabdev
from dotenv import load_dotenv
import os


def main():
    # place your app key and app secret in the .env file
    load_dotenv()  # load environment variables from .env file

    client = schwabdev.Client(os.getenv('app_key'), os.getenv('app_secret'), os.getenv('callback_url'))
    client.update_tokens_auto()  # update tokens automatically (except refresh token)

    """
    # example of using your own response handler, prints to main terminal.
    # the first parameter is used by the stream, the additional parameters are passed to the handler
    def my_handler(message, another_var):
        print(another_var + message)
    client.stream.start(my_handler, "test")
    """

    # example of using the default response handler
    client.stream.start()

    """
    # you can also define a variable for the steamer:
    streamer = client.stream
    streamer.start()
    """

    """
    By default all shortcut requests (below) will be "ADD" commands meaning the list of symbols will be added/appended 
    to current subscriptions for a particular service, however if you want to overwrite subscription (in a particular 
    service) you can use the "SUBS" command. Unsubscribing uses the "UNSUBS" command. To change the list of fields use
    the "VIEW" command.
    """

    # these three do the same thing
    # client.stream.send(client.stream.basic_request("LEVELONE_EQUITIES", "ADD", parameters={"keys": "AMD,INTC", "fields": "0,1,2,3,4,5,6,7,8"}))
    # client.stream.send(client.stream.level_one_equities("AMD,INTC", "0,1,2,3,4,5,6,7,8"), command="ADD")
    client.stream.send(client.stream.level_one_equities("AMD,INTC", "0,1,2,3,4,5,6,7,8"))

    # client.stream.send(client.stream.level_one_options("GOOGL 240712C00200000", "0,1,2,3,4,5,6,7,8")) # key must be from option chains api call.

    client.stream.send(client.stream.level_one_futures("/ES", "0,1,2,3,4,5,6"))

    # client.stream.send(client.stream.level_one_futures_options("keys", "0,1,2,3,4,5"))

    # client.stream.send(client.stream.level_one_forex("EUR/USD", "0,1,2,3,4,5,6,7,8"))

    # client.stream.send(client.stream.nyse_book("keys", "0,1,2,3,4,5,6,7,8"))

    # client.stream.send(client.stream.nasdaq_book("keys", "0,1,2,3,4,5,6,7,8"))

    # client.stream.send(client.stream.options_book("keys", "0,1,2,3,4,5,6,7,8"))

    # client.stream.send(client.stream.chart_equity("keys", "0,1,2,3,4,5,6,7,8"))

    # client.stream.send(client.stream.chart_futures("/ES", "0,1,2,3,4,5,6,7,8"))

    # client.stream.send(client.stream.screener_equity("keys", "0,1,2,3,4,5,6,7,8"))

    # client.stream.send(client.stream.screener_options("keys", "0,1,2,3,4,5,6,7,8"))

    # client.stream.send(client.stream.account_activity("Account Activity", "0,1,2,3"))

    # stop the stream after 60 seconds (since this is a demo
    import time
    time.sleep(60)
    client.stream.stop()


if __name__ == '__main__':
    print("Welcome to the unofficial Schwab interface!\nGithub: https://github.com/tylerebowers/Schwab-API-Python")
    main()  # call the user code above