FROM alpine:3.20
RUN apk add --no-cache lighttpd
COPY deploy/lighttpd/lighttpd.conf /etc/lighttpd/lighttpd.conf
COPY frontend /srv/frontend
EXPOSE 8000
USER lighttpd
CMD ["lighttpd", "-D", "-f", "/etc/lighttpd/lighttpd.conf"]
