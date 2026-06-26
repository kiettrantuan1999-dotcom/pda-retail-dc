from passlib.context import CryptContext
pwd_context=CryptContext(schemes=['pbkdf2_sha256'],deprecated='auto')
def hash_password(password:str)->str: return pwd_context.hash(password[:72])
def verify_password(password:str,password_hash:str)->bool: return pwd_context.verify(password[:72],password_hash)
