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


from tornado.options import define, options
define("port", default=8002, help="run on the given port", type=int)

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
        handlers=[
            (r'/login',LoginHandler),
            (r'/logindev',PushInfoHander),
            (r'/push',GetMessageNeedPush),
        ]
        tornado.web.Application.__init__(self, handlers, **settings)



class PushInfoHander(tornado.websocket.WebSocketHandler):
    """
        注册设备信息
        用于推送消息的类
    """
    waiters = dict()
    def open(self):
        print "a new dev is register"

    def close(self):
        username = self.request.get_secure_cookie("username")
        token = self.application.db.get_user_token(username)
        if token in PushInfoHander.waiters.keys():
            del PushInfoHander.waiters[token]


    def check_origin(self, origin):
        return True

    def on_message(self,data):
        info = json.loads(data)

        print "info" , info
        if info.get('state') == 'register':
            PushInfoHander.waiters[info.get('token')] = self
        if info.get('state') == 'confirm':
            print info.get('rcode')
            self.application.loop.add_callback(GetMessageNeedPush.return_result,"ok",info.get('rcode'),
                                               "登陆成功")

    @classmethod
    def send_push_inf(*args):
        token = args[1]
        rcode = args[2]
        user = PushInfoHander.waiters.get(token)

        if user is not None:
            user.write_message(rcode)
        else:
            print "dev is not online"

    @classmethod
    def keep_socket(*args):
        for i in PushInfoHander.waiters.keys():
            con = PushInfoHander.waiters.get(i)
            con.write_message('beat')

class LoginHandler(tornado.web.RequestHandler):
    def post(self):
        print "有新登录信息需要确认"
        data  = json.loads(self.request.body)
        username = data.get('username')
        password = data.get('password')
        token = self.application.db.check_user(username,password)

        if token is not None:
            self.set_secure_cookie('username',username)
            self.finish(json.dumps([{'state':'ok','token':token}]))
        elif token is None:
            self.finish(json.dumps([{'state':'error'}]))

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
                con.finish(state)
        elif state == "error":
            if rcode in GetMessageNeedPush.request_holder.keys():
                con = GetMessageNeedPush.request_holder.get(rcode)
                GetMessageNeedPush.request_holder.pop(rcode)
                con.finish(state)


if __name__ == '__main__':
    tornado.options.parse_command_line()
    app = Application()
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

