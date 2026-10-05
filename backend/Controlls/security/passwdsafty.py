from pwdlib import PasswordHash
hash=PasswordHash.recommended()

def hashing(passwd:str):
    return hash.hash(passwd)

def verify_passwd(passwd:str,hased_passwd:str):
    return hash.verify(passwd,hased_passwd)