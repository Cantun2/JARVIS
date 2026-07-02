"""Boîte mail factice pour HERMES en mode mock (couvre toutes les catégories)."""

from __future__ import annotations

from jarvis.io.mail import Mail

# Expéditeurs VIP → priorité maximale (règle que l'utilisateur contrôle).
VIP_SENDERS = frozenset({"ceo@stark-industries.com", "marie.direction@boite.fr"})


MOCK_MAILS: tuple[Mail, ...] = (
    Mail(
        id="m1",
        sender="ceo@stark-industries.com",
        subject="URGENT : signature contrat avant 12h",
        body="J'ai besoin de ta validation sur le contrat Wayne avant midi, c'est bloquant.",
    ),
    Mail(
        id="m2",
        sender="marie.direction@boite.fr",
        subject="Deadline rapport trimestriel",
        body="Peux-tu m'envoyer le rapport aujourd'hui ? La deadline est ce soir.",
    ),
    Mail(
        id="m3",
        sender="collegue@boite.fr",
        subject="Question sur l'API de facturation",
        body="Pouvez-vous me confirmer le format attendu pour le champ montant ?",
    ),
    Mail(
        id="m4",
        sender="rh@boite.fr",
        subject="Merci de valider tes congés",
        body="Action requise : valide tes dates de congés dans l'outil avant vendredi.",
    ),
    Mail(
        id="m5",
        sender="client@exemple.com",
        subject="Retour sur la maquette",
        body="Peux-tu jeter un œil à la maquette et me dire ce que tu en penses ?",
    ),
    Mail(
        id="m6",
        sender="notifications@github.com",
        subject="[jarvis-suit] CI passed on main",
        body="Le pipeline d'intégration continue a réussi sur la branche main.",
    ),
    Mail(
        id="m7",
        sender="info@meteo-france.fr",
        subject="Bulletin météo du jour",
        body="Ciel dégagé sur votre région, 22°C l'après-midi.",
    ),
    Mail(
        id="m8",
        sender="newsletter@techcrunch.com",
        subject="This week in AI — newsletter",
        body="Les dernières actualités de l'IA, désabonnez-vous en bas de ce mail.",
    ),
    Mail(
        id="m9",
        sender="noreply@promo-gagnant.biz",
        subject="Félicitations vous avez gagné un iPhone !",
        body="Click here pour réclamer votre cadeau, vous avez gagné à la loterie !",
    ),
)
