##手机加云端，密码更安全


###基本构架

我们设置了两台服务器，一台用于服务页面的登录

另一台用于服务与手机的推送连接，向手机发送登录请求确认和接受手机的确认登录命令

每次用户网页登录帐号后，服务器1接收到请求会先判断用户名存在与否

若存在则向服务器2发送登录请求

否则将返回错误信息

服务器二接收到请求后会向用户登录的手机发送请求

用于接受

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
之后将开始记时，若用户在60s内通过手机确认登录请求，服务器1将收到回复，然后允许此次登录请求

否则将返回出错信息


