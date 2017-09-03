"""
Locano Web Aux routes implementation
"""
import logging
from flask import Blueprint
from flask import render_template, redirect, url_for, request, abort
from db import Channel


CHANNELS_ROOT = '/channels'
STATIC_FOLDER = 'static'


channels = Blueprint('channel', __name__,
                     template_folder='templates',
                     static_folder=STATIC_FOLDER)


@channels.route('/')
@channels.route('/<uchid>')
def channel_root(uchid=None):
    if uchid:
        c = Channel.by_uchid_str(uchid)
        if c:
            return render_template('channel.html', channel=c)
    abort(404)


@channels.route('/scripts/<rest>')
@channels.route('/images/<rest>')
@channels.route('/css/<rest>')
def channel_muse_adjust_scripts(rest=None):
    if rest:
        fpath = request.path.replace(CHANNELS_ROOT + '/', '')
        url = url_for('.static', filename=fpath)
        if request.query_string:
            url += '?' + request.query_string.decode("utf-8")
        return redirect(url)
    else:
        return render_template('page_not_found.html'), 404


def create_webaux(app):
    logging.info("Creating Web Aux")
    # Register the Channels blueprint.
    app.register_blueprint(channels, url_prefix=CHANNELS_ROOT)

    app.config.update(EXPLAIN_TEMPLATE_LOADING=True)

    logging.info("Done")
    return app
