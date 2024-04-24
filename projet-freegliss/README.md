L'objectif de ce cas était de scraper toutes les informations possibles concernant les produits "Skis" dur site internet FreeGliss. Ensuite, faire une visualiation sur PowerBi des résultats pour avoir une vue d'ensemble des produits proposés, les marques, les prix, etc...

Vous retrouerez deux fichiers python :
- [Freegliss](#freegliss.ipynb) : script python qui se charge du scraping des informations de chaque ski 
- [Bot scrap](#bot-scrap.ipynb) : Notre objectif est de développer un bot capable d'automatiser la recherche des stocks de chaque modèle de ski disponible. Le bot simule le processus d'ajout de ski au panier jusqu'à ce qu'un message indique que le produit n'est plus en stock. Ensuite, il comptabilise le nombre d'ajouts effectués pour estimer la disponibilité du produit.
Une particularité importante est que chaque modèle de ski est disponible dans différentes catégories (représentant l'état du ski) et dans plusieurs tailles. Par conséquent, le bot doit effectuer ce processus de comptage pour chaque modèle de ski, pour chaque catégorie et pour chaque taille disponible.
