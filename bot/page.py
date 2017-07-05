import logging
import fbmq
from bot.config import CONFIG

DUMP_PARAMS = True

def dump_params(**kwargs):
    if DUMP_PARAMS:
        if kwargs is not None:
            for key in kwargs:
                if key != "self":
                    logging.debug("%s = %s", key, vars(kwargs[key]))


class BotPage(fbmq.Page):
    def __init__(self):
        super().__init__(CONFIG['ACCESS_TOKEN'])
        self.greeting("Hi {{user_first_name}}, welcome to Locano Chatbot!")
        self.show_starting_button("Show Help")
        self.show_persistent_menu([
            fbmq.Template.ButtonPostBack('Help', 'MENU_PAYLOAD/1'),
            fbmq.Template.ButtonPostBack('Announce', 'MENU_PAYLOAD/2'),
            fbmq.Template.ButtonPostBack('Scan', 'MENU_PAYLOAD/3')])

    def on_menu(self, payload, event):
        dump_params(**locals())
        sender_id = event.sender_id
        item_id = payload.split('/')[1]
        logging.debug("[U#%s >] [on_menu] %s", sender_id, item_id)
        page.send(sender_id, "thank you! you clicked button no. %s", item_id)

    def on_message(self, event):
        dump_params(**locals())
        sender_id = event.sender_id
        message = event.message_text
        logging.debug("[U#%s >] [on_message] %s", sender_id, message)
        page.send(sender_id, "thank you! your message is '%s'" % message)

    def on_after_send(self, payload, response):
        dump_params(**locals())
        logging.debug("[U#%s <] [on_after_send] %s",
                      payload.recipient.id,
                      payload.message.text)


    def on_echo(self, event):
        dump_params(**locals())
        logging.debug("[U#%s <] [on_echo] %s",
                      event.sender_id,
                      event.message_text)

page = BotPage()


@page.callback(['MENU_PAYLOAD/(.+)'])
def click_persistent_menu(payload, event):
    page.on_menu(payload, event)


@page.handle_message
def message_handler(event):
    page.on_message(event)


@page.after_send
def after_send(payload, response):
    page.on_after_send(payload, response)


@page.handle_echo
def echo_handler(event):
    page.on_echo(event)
