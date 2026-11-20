"""Jouer aux dames à deux dans le terminal : chaque joueur tape son coup, comme c3 d4."""
from dames import Partie
from exceptions import ErreurDames


def lire_coup(texte: str) -> tuple[str, str]:
    """« c3 d4 », « c3-d4 » ou « d4xf6 » donnent ("c3", "d4"). Sinon ValueError."""
    texte = texte.strip()

    parties = texte.replace("-", " ").replace("x", " ").split()

    if len(parties) != 2:
        raise ValueError("tapez deux cases")

    return parties[0], parties[1]


def main() -> int:
    partie = Partie()

    print("Bienvenue dans le jeu de dames !")
    print(partie.plateau)

    while partie.gagnant is None:
        print(f"Au tour des {partie.trait}s.")

        texte = input("Votre coup (ex: c3 d4 ou quitter) : ")

        if texte.strip().lower() == "quitter":
            print("Partie abandonnée.")
            return 0

        try:
            depart, arrivee = lire_coup(texte)
            coup = partie.jouer(depart, arrivee)

            print(coup)
            print(partie.plateau)

        except (ValueError, ErreurDames) as erreur:
            print(f"Refusé : {erreur}")

    print(f"Les {partie.gagnant}s gagnent !")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
