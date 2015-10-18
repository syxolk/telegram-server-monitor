import json

class Persistence:
    def __init__(self):
        try:
            with open('users.json') as file:
                self.users = json.load(file)
        except FileNotFoundError:
            # Initialize for first start
            self.users = []

    def registerUser(self, id):
        self.users.append(id)
        self.save()

    def unregisterUser(self, id):
        self.users.remove(id)
        self.save()

    def isRegisteredUser(self, id):
        return id in self.users

    def allUsers(self):
        return self.users

    def save(self):
        with open('users.json', 'w') as outfile:
            json.dump(self.users, outfile)
