#coding=utf-8
import os.path
import uuid
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import redis
import json
from UserAction import UserAction
import tornado.websocket
import time


from tornado.options import define, options
define("port", default=8001, help="run on the given port", type=int)

class Application(tornado.web.Application):
    def __init__(self):
        template_path=os.path.join(os.path.dirname(__file__), "templates")
        static_path=os.path.join(os.path.dirname(__file__), "static")
        settings = {
        #    "xsrf_cookies": True,
            "login_url": "/login",
            'cookie_secret': "CkwXIkG6RXs15skVeMBhdbJKt0QSqk1tivD1smsr98Y=",
            'template_path':template_path,
            'static_path':static_path,
        }
        self.flag = False
        self.cache = redis.StrictRedis(host='localhost', port=6379)
        self.db = UserAction()
        self.loop = tornado.ioloop.IOLoop.current()
        #self.loop.add_handler(1,PushInfoHander.keep_socket,tornado.ioloop.IOLoop.WRITE)
        handlers=[
            (r'/',MainPageHandler),
            (r'/confirm',LoginConfirmHandler),
            (r'/login',LoginHandler),
            (r'/logout',LogoutHandler),
            (r'/registerDev',PushInfoHander),
            (r'/push',GetMessageNeedPush),
        ]
        tornado.web.Application.__init__(self, handlers, **settings)

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("username")

class LoginHandler(tornado.web.RequestHandler):
    """
        登陆
    """
    def get(self):
        self.render('login.html')

    def post(self):
        username = self.get_argument('username')
        password = self.get_argument('password')
        token = self.application.db.check_user(username,password)
        message = {}
        if token is not None:
            self.set_secure_cookie('username',username)
            message['state'] = 'ok'
            message['detail'] = 'login success'
            print json.dumps([message])
            self.finish(json.dumps(message))
        else:
            message['state'] = 'error'
            message['detail'] = 'login faile'
            self.finish(json.dumps(message))

    def get_current_user(self):
        return self.get_secure_cookie("username")

class LogoutHandler(tornado.web.RequestHandler):
    """
        注销
    """
    def get(self):
        self.clear_cookie('username')
        message = {'state':'ok','detail':'logout success'}
        self.finish(json.dumps(message))

class PushInfoHander(tornado.websocket.WebSocketHandler):
    """
        注册设备信息
        用于推送消息的类
    """
    waiters = dict()
    def open(self):
        print "hehe"

    def close(self):
        username = self.request.get_secure_cookie("username")
        token = self.application.db.get_user_token(username)
        if token in PushInfoHander.waiters.keys():
            del PushInfoHander.waiters[token]

    @classmethod
    def send_push_inf(*args):
        token = args[1]
        rcode = args[2]
        user = PushInfoHander.waiters.get(token)

        if user is not None:
            user.write_message(rcode)
        else:
            print "dev is not online"

    def check_origin(self, origin):
        return True

    def on_message(self,username):
        time.sleep(5)
        print ""
        self.write_message('asd')
        # token = self.application.db.get_user_token(username)
        # if token not in PushInfoHander.waiters.keys():
        #     PushInfoHander.waiters[token] = self

    @classmethod
    def keep_socket(*args):
        for i in PushInfoHander.waiters.keys():
            con = PushInfoHander.waiters.get(i)
            con.write_message('beat')


class GetMessageNeedPush(tornado.web.RequestHandler):
    """
        用于从LoginRequest中获取相关信息
        需要有token和detail 放在get方法的头里
        return_result用于向指定con发送成功信息
    """
    request_holder = {}
    @tornado.web.asynchronous
    def get(self):
        token = self.request.headers.get('token')
        rcode = self.request.headers.get('rcode')
        #推送信息
        self.application.loop.add_callback(PushInfoHander.send_push_inf,token,rcode)
        #将request放入连接池，用rcode表示
        if rcode not in GetMessageNeedPush.request_holder.keys():
            GetMessageNeedPush.request_holder[rcode] = self

        self.application.loop.call_later(60,GetMessageNeedPush.return_result,
                                         'error',rcode,"登陆超时")

    @classmethod
    def return_result(*args):
        state = args[1]
        rcode = args[2]
        confirm_info = args[3]
        if state == "ok":
            if rcode in GetMessageNeedPush.request_holder.keys():
                con = GetMessageNeedPush.request_holder.get(rcode)
                GetMessageNeedPush.request_holder.pop(rcode)
                con.finish(confirm_info)
        elif state == "error":
            if rcode in GetMessageNeedPush.request_holder.keys():
                con = GetMessageNeedPush.request_holder.get(rcode)
                GetMessageNeedPush.request_holder.pop(rcode)
                con.finish(confirm_info)

# class LoginConfirmHandler(BaseHandler):
#     """
#         用于接收确认端发来的信息
#         需要被认证的设备发送rcode
#     """
#     @tornado.web.authenticated
#     def post(self):
#         token = self.application.db.get_user_token(self.current_user)
#         rcode = self.get_argument('rcode')
#         if rcode == str(self.application.cache.hget("request_map",token)):
#             self.application.loop.add_callback(GetMessageNeedPush.return_result,
#                                                "ok",rcode,"成功验证")
#         self.finish("您已经成功验证")

class LoginConfirmHandler(BaseHandler):
    """
        用于接收确认端发来的信息
        需要被认证的设备发送rcode
    """
    @tornado.web.authenticated
    def post(self):
        token = self.application.db.get_user_token(self.current_user)
        rcode = self.get_argument('rcode')
        if rcode == str(self.application.cache.hget("request_map",token)):
            self.application.loop.add_callback(GetMessageNeedPush.return_result,
                                               "ok",rcode,"成功验证")
        self.finish("您已经成功验证")

class MainPageHandler(BaseHandler):
    """
        用于显示主页面
    """
    @tornado.web.authenticated
    def get(self):
        self.render('confirm_page.html',user = self.current_user)


if __name__ == '__main__':
    tornado.options.parse_command_line()
    app = Application()
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

