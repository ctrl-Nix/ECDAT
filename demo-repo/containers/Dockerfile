
FROM ubuntu:20.04

# WEAK: Old OpenSSL with TLS 1.0 support
RUN apt-get update && apt-get install -y \
    libssl1.1 \
    openssl=1.1.1f-1ubuntu2 \
    libgcrypt20 \
    libnss3 \
    python3-pip

# WEAK: Install pycrypto
RUN pip3 install pycrypto==2.6.1
RUN pip3 install pycryptodome==3.15.0

# WEAK: Install md5 npm package
COPY deps/package.json /tmp/package.json
RUN npm install --prefix /tmp

# WEAK: OpenSSL config with weak protocols
RUN echo 'ssl_protocols = TLSv1 TLSv1.1 TLSv1.2' >> /etc/ssl/openssl.cnf

CMD ["python3", "app.py"]
