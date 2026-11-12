# Réglages du réseau local : à adapter à votre installation, puis `make deploy`.
# Chaque valeur peut aussi être donnée sur la ligne de commande, par exemple :
#   make deploy ULTIMATE=192.168.0.64

# Adresse IP du PC qui fait tourner le serveur (`make server`).
# Elle est pré-remplie dans le champ SERVEUR du C64, qui reste modifiable au clavier.
SERVEUR_IP ?= 192.168.1.55

# Port TCP du serveur : celui qu'il écoute et celui que le C64 appelle.
SERVEUR_PORT ?= 6464

# Adresse IP du C64 Ultimate, pour `make deploy` (API REST de l'Ultimate).
ULTIMATE ?= 192.168.1.27
