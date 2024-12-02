FROM ubuntu:22.04
MAINTAINER Odoo S.A. <info@odoo.com>

COPY ./odoo_16.0+e.latest_all.deb odoo.deb
COPY ./postgresql-client-12_12.2-4_amd64.deb postgres-12.2.deb
SHELL ["/bin/bash", "-xo", "pipefail", "-c"]

# Generate locale C.UTF-8 for postgres and general locale data
ENV LANG C.UTF-8
RUN DEBIAN_FRONTEND=noninteractive\
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        dirmngr \
        fonts-noto-cjk \
        gnupg \
        libssl-dev \
        node-less \
        npm \
        python3-num2words \
        python3-pdfminer \
        python3-pip \
        python3-phonenumbers \
        python3-pyldap \
        python3-qrcode \
        python3-renderpm \
        python3-setuptools \
        python3-slugify \
        python3-vobject \
        python3-watchdog \
        python3-xlrd \
        python3-xlwt \
        xz-utils \
        zbar-tools \
        poppler-utils \
        unixodbc

 
RUN  curl -o wkhtmltox.deb -sSL https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_amd64.deb \
&& DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ./wkhtmltox.deb \
&& rm -rf /var/lib/apt/lists/* wkhtmltox.deb
RUN pip3 install --upgrade pip
RUN pip3 uninstall -y gevent
# install custom libraries version from requeriments.txt
COPY ./requeriments.txt requeriments.txt
RUN pip3 install -r requeriments.txt

RUN npm install -g rtlcss

# Install Odoo
RUN apt-get update \
    && apt-get -y install --no-install-recommends ./odoo.deb \
    && rm -rf /var/lib/apt/lists/* odoo.deb
    
RUN apt-get update \
    && apt-get -y install --no-install-recommends ./postgres-12.2.deb \
    && rm -rf /var/lib/apt/lists/* postgres-12.2.deb
# Copy entrypoint script and Odoo configuration file
COPY ./entrypoint.sh /
COPY ./etc/odoo.conf /etc/odoo/
RUN apt-get update
RUN apt-get install -y lsb-release
RUN curl https://packages.microsoft.com/keys/microsoft.asc | tee /etc/apt/trusted.gpg.d/microsoft.asc
RUN curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | tee /etc/apt/sources.list.d/mssql-release.list
RUN apt-get update
RUN ACCEPT_EULA=Y apt-get install -y msodbcsql17
# Set permissions and Mount /var/lib/odoo to allow restoring filestore and /mnt/extra-addons for users addons
RUN chown odoo:odoo /etc/odoo/odoo.conf \
    && mkdir -p /mnt/extra-addons \
    && chown -R odoo:odoo /mnt/extra-addons \
    && chmod 777 -R /mnt/extra-addons \    
    && mkdir -p /mnt/out_files \
    && chmod 777 -R /mnt/out_files \
    && chown -R odoo:odoo /mnt/out_files \
    && chown -R odoo:odoo /var/lib/odoo

VOLUME ["/etc/odoo","/var/lib/odoo","/mnt/extra-addons","/mnt/out_files"]
RUN chmod 777 -R /var/lib/odoo

# Expose Odoo services
EXPOSE 8069 8071 8072

# Set the default config file
ENV ODOO_RC /etc/odoo/odoo.conf

COPY wait-for-psql.py /usr/local/bin/wait-for-psql.py

# Set default user when running the container
USER odoo

ENTRYPOINT ["/entrypoint.sh"]
CMD ["odoo"]


##After do changes of custom pandas because disapears 