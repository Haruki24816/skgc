class ServerException(Exception):
    pass

class ServerInitException(ServerException):
    pass

class ServerDataError(ServerException):
    pass

class ServerStartingException(ServerException):
    pass

class ServerProcessError(ServerException):
    pass

class ServerOutputException(ServerException):
    pass

class ServerInputException(ServerException):
    pass
