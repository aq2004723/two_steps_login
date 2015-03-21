#coding=utf-8

import os.path
import uuid
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.httpclient
from UserAction import UserAction
import json
import redis


from tornado.options import define, options
import config

define("port", default=8000, help="run on the given port", type=int)

class Application(tornado.web.Application):
    def __init__(self):
        self.user_action = UserAction()
        self.cache = redis.StrictRedis(host='localhost', port=6379)
        template_path=os.path.join(os.path.dirname(__file__), "templates")
        static_path=os.path.join(os.path.dirname(__file__), "static")
        settings = {
            'cookie_secret': config.COOKIE_SECRET,
            'template_path':template_path,
            'static_path':static_path,
        }
        handlers=[(r'/', IndexHandler),
        ]
        tornado.web.Application.__init__(self, handlers, **settings)

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('webrequest.html')

    def post(self):
        username = self.get_argument("username")
        token = self.application.user_action.get_user_token(username)
        rcode = str(uuid.uuid4())
        self.application.cache.hset("request_map",token,rcode)
        if not token is None:
            headers = {'token':token,'rcode':rcode}
            request = tornado.httpclient.HTTPRequest(url=config.url_of_ConfirmRequest,
                method="GET",headers = headers,connect_timeout=120,
                request_timeout=120)
            http_client = tornado.httpclient.HTTPClient()
            response = http_client.fetch(request)
            self.application.cache.hdel("request_map",token)
            if response.error:
                print "Error:", response.error
            else:
                print response.body
                self.render('result.html',state = response.body)
        else:
            message = {'state':'error','detail':'username is not exits'}
            self.render('result.html',state='usererror')

if __name__ == '__main__':
    tornado.options.parse_command_line()
    app = Application()
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
