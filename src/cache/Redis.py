# connect to redis server
import redis

r = redis.Redis(host='localhost', port=6379, db=0)


class Redis:

    def __init__(self):
        self.r = redis.Redis(host='localhost', port=6379, db=0)


    def test_connection(self):
        self.r.set('foo', 'bar')

    def set(self, key, value):
        self.r.set(key, value)

    def get(self, key):
        res = self.r.get(key)
        return res.decode('utf-8')

    def delete(self, key):
        self.r.delete(key)

    def append_to_list(self, key, value):
        self.r.rpush(key, value)

    def get_list(self, key):
        res = self.r.lrange(key, 0, -1)
        for i in range(len(res)):
            res[i] = res[i].decode('utf-8')
        return res



# test redis
r = Redis()
r.test_connection()


# test append to list
print(len(set(r.get_list('jobs'))))

