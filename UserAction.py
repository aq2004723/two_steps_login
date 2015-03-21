#coding = utf-8

import pymongo
import uuid
import config


class UserAction:
    def __init__(self):
        self.con = pymongo.Connection("localhost", 27017)
        self.db = self.con.twosteplogin

    def __delete__(self):
        self.con.close()


    def get_user_token(self,username):
        user = self.db.users.find_one({'username':username},{'token':1})
        if not user is None:
            return user.get('token')
    	else:
    		return None

    def register(self,username,password):
        if self.db.users.find_one({'username':username}) is None:
            token = str(uuid.uuid3(config.TOKEN_NAME_SPACE,username))
            user = {
                'username':username,
                'password':str(uuid.uuid5(config.PASSWORD_NAME_SPACE,str(password))),
                'token':token
            }
            self.db.users.insert(user)
            return token
        else:
            return None 

    def check_user(self,username,password):
        user = self.db.users.find_one({'username':username,
            'password':str(uuid.uuid5(config.PASSWORD_NAME_SPACE,str(password)))})
        if not user is None:
            return user.get('token')
        else:
            return None


if __name__ == '__main__':
    t = UserAction()
    #t.register('1','1')
    for i in t.db.users.find():
        print i


