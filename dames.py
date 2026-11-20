"""Le jeu de dames en objets : cases, pièces, plateau et partie.

Règles du jeu de dames international (plateau de 10 x 10), simplifiées : une seule prise par
coup (pas de rafle) et pas de règle de la majorité.
"""
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

from exceptions import CoupInvalideError

COLONNES = "abcdefghij"
TAILLE = 10
DIAGONALES = [(1, 1), (-1, 1), (1, -1), (-1, -1)]


def adversaire(couleur: str) -> str:
    """La couleur de l'autre joueur."""
    return "noir" if couleur == "blanc" else "blanc"


# --- Étape 1 : la case ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Case:
    """Une case, de a1 à j10. Immuable : on peut la hacher et s'en servir comme clé."""
    colonne: str
    ligne: int

    def __post_init__(self):
        if not isinstance(self.colonne, str) or len(self.colonne) != 1 or self.colonne not in COLONNES:
            raise ValueError(f"colonne invalide : {self.colonne!r}")

        if not isinstance(self.ligne, int) or isinstance(self.ligne, bool) or not (1 <= self.ligne <= TAILLE):
            raise ValueError(f"ligne invalide : {self.ligne!r}")
        
    @classmethod
    def depuis_nom(cls, nom: str) -> "Case":
        try:
            return cls(nom[0], int(nom[1:]))
        except (ValueError, IndexError):
            raise ValueError(f"nom de case invalide : {nom!r}") from None

    @property
    def est_noire(self) -> bool:
        """On ne joue que sur les cases noires ; a1 est noire."""
        return (COLONNES.index(self.colonne) + self.ligne) % 2 == 1

    def decaler(self, dc: int, dl: int) -> "Case | None":
        """La case située dc colonnes et dl lignes plus loin, ou None si on sort du plateau."""
        nouvelle_colonne = COLONNES.index(self.colonne) + dc
        nouvelle_ligne = self.ligne + dl

        if not (0 <= nouvelle_colonne < TAILLE):
            return None

        if not (1 <= nouvelle_ligne <= TAILLE):
            return None

        return Case(COLONNES[nouvelle_colonne], nouvelle_ligne)

    def __str__(self) -> str:
        return f"{self.colonne}{self.ligne}"


    def en_case(case: "Case | str") -> "Case":
        """Convertit une chaîne en Case, ou retourne la Case reçue."""
        if isinstance(case, Case):
            return case

        if isinstance(case, str):
            return Case.depuis_nom(case)

        raise ValueError(f"case invalide : {case!r}")



# --- Étape 2 : les pièces ------------------------------------------------------------------------
class Piece(ABC):
    """Une pièce : une couleur qui ne change jamais. Elle ne connaît pas sa case :
    c'est le plateau qui sait où sont les pièces."""

    COULEURS = ("blanc", "noir")
    LETTRE = "?"
    NOM = "pièce"
    FEMININ = False

    def __init__(self, couleur: str):
        """Refuse une couleur autre que "blanc" ou "noir" (ValueError)."""
        if couleur not in self.COULEURS:
            raise ValueError(f"couleur invalide : {couleur!r}")
        self._couleur = couleur

    @property
    def couleur(self) -> str:
        """Lecture seule : pas de setter."""
        return self._couleur

    @property
    def sens(self) -> int:
        """+1 pour les blancs, -1 pour les noirs."""
        return 1 if self.couleur == "blanc" else -1

    @property
    def symbole(self) -> str:
        """Majuscule pour les blancs, minuscule pour les noirs."""
        return self.LETTRE.upper() if self.couleur == "blanc" else self.LETTRE.lower()

    def est_adverse(self, autre: "Piece | None") -> bool:
        """Vrai si autre est une pièce de l'autre couleur."""
        return autre is not None and self.couleur != autre.couleur

    @abstractmethod
    def deplacements(self, case: Case, plateau: "Plateau") -> set[Case]:
        """Les cases où la pièce peut aller depuis case, sans prendre."""
        pass

    @abstractmethod
    def prises(self, case: Case, plateau: "Plateau") -> dict[Case, Case]:
        """Les prises possibles depuis case."""
        pass

    def promouvoir(self, case: Case) -> "Piece":
        """La pièce qui occupe case après le coup."""
        return self

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.couleur!r})"

    def __str__(self) -> str:
        if self.couleur == "blanc":
            adjectif = "blanche" if self.FEMININ else "blanc"
        else:
            adjectif = "noire" if self.FEMININ else "noir"

        return f"{self.NOM} {adjectif}"


# --- Étape 3 : le plateau ------------------------------------------------------------------------
def en_case(case):
    if isinstance(case, Case):
        return case
    if isinstance(case, str):
        return Case.depuis_nom(case)
    raise ValueError(f"case invalide : {case!r}")


def ordre(case: Case):
    return (case.ligne, COLONNES.index(case.colonne))


class Plateau:
    """Le plateau A des pièces (composition), rangées dans un dict privé case -> pièce."""

    def __init__(self):
        self._pieces: dict[Case, Piece] = {}

    @classmethod
    def depuis_dict(cls, pieces: dict[str, str]) -> "Plateau":
        """Constructeur alternatif : Plateau.depuis_dict({"c3": "P", "f6": "d"}).
        P = pion, D = dame ; majuscule pour les blancs, minuscule pour les noirs."""
        plateau = cls()
        for nom, lettre in pieces.items():
            couleur = "blanc" if lettre.isupper() else "noir"
            classe = Pion if lettre.upper() == "P" else Dame
            plateau.placer(nom, classe(couleur))
        return plateau

    @classmethod
    def position_initiale(cls) -> "Plateau":
        plateau = cls()

        for ligne in range(1, 5):
            for colonne in COLONNES:
                case = Case(colonne, ligne)
                if case.est_noire:
                    plateau.placer(case, Pion("blanc"))

        for ligne in range(7, 11):
            for colonne in COLONNES:
                case = Case(colonne, ligne)
                if case.est_noire:
                    plateau.placer(case, Pion("noir"))

        return plateau

    def placer(self, case: "Case | str", piece: Piece) -> None:
        """Pose une pièce. ValueError si la case est blanche ou déjà occupée."""
        case = en_case(case)

        if not case.est_noire:
            raise ValueError("impossible de placer une pièce sur une case blanche")

        if case in self._pieces:
            raise ValueError(f"case déjà occupée : {case}")

        self._pieces[case] = piece

    def __getitem__(self, case: "Case | str") -> "Piece | None":
        """plateau["c3"] : la pièce sur la case, ou None si elle est vide."""
        case = en_case(case)
        return self._pieces.get(case)

    def __contains__(self, case: "Case | str") -> bool:
        """"c3" in plateau : vrai si la case est occupée."""
        case = en_case(case)
        return case in self._pieces

    def __len__(self) -> int:
        """Le nombre de pièces sur le plateau."""
        return len(self._pieces)

    def __iter__(self):
        """Parcourt les cases occupées, ligne par ligne, de gauche à droite."""
        return iter(sorted(self._pieces, key=ordre))

    def compter(self, couleur: str) -> int:
        return sum(1 for case in self if self[case].couleur == couleur)

    # --- Étape 6
    def prises_possibles(self, couleur: str):
        """Toutes les prises possibles d'un joueur."""
        resultats = {}

        for case in self:
            piece = self[case]

            if piece.couleur == couleur:
                prises = piece.prises(case, self)

                if prises:
                    resultats[case] = prises

        return resultats

    def coups_possibles(self, couleur: str):
        """Les coups autorisés, triés. S'il existe des prises, seules les prises comptent."""

        prises = self.prises_possibles(couleur)

        # Si une prise existe, elle est obligatoire
        if prises:
            coups = []

            for depart in prises:
                for arrivee in sorted(prises[depart], key=ordre):
                    coups.append((depart, arrivee))

            return coups

        # Sinon, récupérer les déplacements simples
        coups = []

        for depart in self:
            piece = self[depart]

            if piece.couleur == couleur:
                destinations = piece.deplacements(depart, self)

                for arrivee in sorted(destinations, key=ordre):
                    coups.append((depart, arrivee))

        return coups

    def deplacer(self, depart, arrivee):
        """Joue un coup, renvoie la pièce prise ou None."""

        depart = en_case(depart)
        arrivee = en_case(arrivee)

        piece = self[depart]

        # Vérifier que la case de départ contient une pièce
        if piece is None:
            raise CoupInvalideError(
                str(depart),
                str(arrivee),
                "aucune pièce sur la case de départ"
            )

        couleur = piece.couleur

        # Vérifier les prises possibles
        prises = self.prises_possibles(couleur)

        if prises:
            # La prise est obligatoire
            if depart not in prises or arrivee not in prises[depart]:
                raise CoupInvalideError(
                    str(depart),
                    str(arrivee),
                    "la prise est obligatoire"
                )

            case_prise = prises[depart][arrivee]
            piece_prise = self[case_prise]

        else:
            # Vérifier les déplacements simples
            destinations = piece.deplacements(depart, self)

            if arrivee not in destinations:
                raise CoupInvalideError(
                    str(depart),
                    str(arrivee),
                    "déplacement interdit"
                )

            piece_prise = None
            case_prise = None

        # Exécuter le coup après vérification
        if case_prise is not None:
            del self._pieces[case_prise]

        del self._pieces[depart]

        # Vérifier la promotion
        self._pieces[arrivee] = piece.promouvoir(arrivee)

        return piece_prise

    # --- Étape 8
    def vers_dict(self):
        return {
            str(case): self[case].symbole
            for case in self
        }

    # --- Affichage (fourni)
    def __repr__(self) -> str:
        return f"<Plateau : {self.compter('blanc')} blancs, {self.compter('noir')} noirs>"

    def __str__(self) -> str:
        lignes = []
        for ligne in range(TAILLE, 0, -1):
            cases = []
            for colonne in COLONNES:
                case = Case(colonne, ligne)
                piece = self[case]
                cases.append(piece.symbole if piece else "." if case.est_noire else " ")
            lignes.append(f"{ligne:>2}  " + " ".join(cases))
        lignes.append("    " + " ".join(COLONNES))
        return "\n".join(lignes)


# --- Étape 4 : le pion ---------------------------------------------------------------------------
class Pion(Piece):
    LETTRE = "P"
    NOM = "pion"

    def deplacements(self, case, plateau):
        """Une case en diagonale, vers l'avant, si elle est libre."""
        resultats = set()

        for dc in (-1, 1):
            destination = case.decaler(dc, self.sens)

            if destination is not None and plateau[destination] is None:
                resultats.add(destination)

        return resultats

    def prises(self, case, plateau):
        """Sauter une pièce adverse voisine (avant ou arrière) vers la case libre derrière."""
        resultats = {}

        for dc, dl in DIAGONALES:
            voisine = case.decaler(dc, dl)
            destination = case.decaler(2 * dc, 2 * dl)

            if voisine is None or destination is None:
                continue

            piece_voisine = plateau[voisine]

            if (
                piece_voisine is not None
                and self.est_adverse(piece_voisine)
                and plateau[destination] is None
            ):
                resultats[destination] = voisine

        return resultats

    # --- Étape 6
        # --- Étape 6
    def promouvoir(self, case):
        """Sur la dernière ligne (10 pour les blancs, 1 pour les noirs), le pion devient dame."""
        if self.couleur == "blanc" and case.ligne == 10:
            return Dame(self.couleur)

        if self.couleur == "noir" and case.ligne == 1:
            return Dame(self.couleur)

        return self


# --- Étape 5 : la dame ---------------------------------------------------------------------------
class Dame(Piece):
    LETTRE = "D"
    NOM = "dame"
    FEMININ = True

    def deplacements(self, case, plateau):
        """La dame se déplace sur toutes les cases libres de ses diagonales."""
        resultats = set()

        for dc, dl in DIAGONALES:
            destination = case.decaler(dc, dl)

            while destination is not None and plateau[destination] is None:
                resultats.add(destination)
                destination = destination.decaler(dc, dl)

        return resultats

    def prises(self, case, plateau):
        """La dame prend une pièce adverse à distance sur une diagonale."""
        resultats = {}

        for dc, dl in DIAGONALES:
            destination = case.decaler(dc, dl)

            # Parcourir les cases libres avant une éventuelle pièce
            while destination is not None and plateau[destination] is None:
                destination = destination.decaler(dc, dl)

            if destination is None:
                continue

            piece = plateau[destination]

            # Une pièce de sa couleur bloque le déplacement
            if not self.est_adverse(piece):
                continue

            # Chercher les cases libres derrière la pièce adverse
            arrivee = destination.decaler(dc, dl)

            while arrivee is not None and plateau[arrivee] is None:
                resultats[arrivee] = destination
                arrivee = arrivee.decaler(dc, dl)

        return resultats

# --- Étape 7 : la partie -------------------------------------------------------------------------
@dataclass(frozen=True)
class Coup:
    numero: int
    couleur: str
    depart: str
    arrivee: str
    prise: bool = False

    def __str__(self):
        separateur = "x" if self.prise else "-"
        return f"{self.numero}. {self.depart}{separateur}{self.arrivee}"


class Partie:

    def __init__(self, plateau=None):
        self.plateau = plateau if plateau is not None else Plateau.position_initiale()
        self.trait = "blanc"
        self.historique = []

    def jouer(self, depart, arrivee):
        piece = self.plateau[depart]

        if piece is not None and piece.couleur != self.trait:
            raise CoupInvalideError(
                str(depart),
                str(arrivee),
                f"c'est aux {self.trait}s de jouer"
            )

        numero = len(self.historique) + 1
        couleur = self.trait

        piece_prise = self.plateau.deplacer(depart, arrivee)

        coup = Coup(
            numero,
            couleur,
            str(en_case(depart)),
            str(en_case(arrivee)),
            piece_prise is not None
        )

        self.historique.append(coup)

        self.trait = adversaire(self.trait)

        return coup

    @property
    def gagnant(self):
        if self.plateau.compter("blanc") == 0:
            return "noir"

        if self.plateau.compter("noir") == 0:
            return "blanc"

        if not self.plateau.coups_possibles(self.trait):
            return adversaire(self.trait)

        return None

    # --- Étape 8
    def sauvegarder(self, chemin):
        donnees = {
            "trait": self.trait,
            "pieces": self.plateau.vers_dict()
        }

        with open(chemin, "w", encoding="utf-8") as fichier:
            json.dump(donnees, fichier, indent=4, ensure_ascii=False)

    @classmethod
    def charger(cls, chemin):
        with open(chemin, "r", encoding="utf-8") as fichier:
            donnees = json.load(fichier)

        plateau = Plateau.depuis_dict(donnees["pieces"])

        partie = cls(plateau)
        partie.trait = donnees["trait"]

        return partie
