# CAE

This paltform is a container app engine base on [docker](https://github.com/moby/moby) and [traefik](https://github.com/traefik/traefik).

## Features

- SSH entrance to container instance.
- Container instance and image manage.
- L7 ingress rule manage.


## Quickstart

```
docker-compose up -d
```

Open `http://localhost:5000` in your browser. Default auth user and password is `traefik:traefik`.

Create instance you can use the [base-image](https://github.com/Arvintian/base-image), e.g `arvintian/base-image:1.3.2`.

SSH connect to instance `ssh {instance name}:{inner user}@localhost -p 2222`.