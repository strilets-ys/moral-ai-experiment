from django.core.management.base import BaseCommand
from experiment.models import Dilemma, StanceCombination


# Greene dilemmas (6 total: 2 personal + 2 impersonal + 2 nonmoral)
GREENE_DILEMMAS = [
    # Personal - Action
    {
        "code": "Terrorist_Negotiation",
        "author": "greene",
        "category": "personal",
        "dilemma_type": "action",
        "researcher": "G",
        "text": "Emilia is negotiating with a powerful and determined terrorist who is about to set off a bomb in a crowded area. Her advantage is that she has his innocent teenage son in her custody. There is only one thing that she can do to stop him from detonating his bomb, which will kill thousands of people if detonated. To stop him, she must contact him over the satellite hook-up that she has established and, in front of the camera, she breaks one of his son's arms and then threatens to break the other one if he does not give himself up. Emilia accepts to do this action.",
        "subject": "Emilia's",
        "low_rating_framework": "deontological",
    },
    # Personal - Omission
    {
        "code": "Submarine_Oxygen",
        "author": "greene",
        "category": "personal",
        "dilemma_type": "omission",
        "researcher": "G",
        "text": "Azzo is the captain of a military submarine travelling underneath a large iceberg. An on-board explosion has caused him to lose a large part of the oxygen supply and has injured one of his crew who is quickly losing blood. The injured crew member is going to die from his wounds no matter what happens. The remaining oxygen supply is not sufficient for the entire crew to make it to the surface. The only way to save the other crew members is to shoot dead the injured crew member so that there will be just enough oxygen for the rest of the crew to survive. Azzo decides to not kill the fatally injured crew member.",
        "subject": "Azzo’s",
        "low_rating_framework": "utilitarian",
    },
    # Impersonal - Omission
    {
        "code": "Hospital_Fumes",
        "author": "greene",
        "category": "impersonal",
        "dilemma_type": "omission",
        "researcher": "G",
        "text": "Anna is the late-night watch nurse in a hospital. Due to an accident in the building next door, there are deadly fumes rising up through the hospital's ventilation system. In a certain room of the hospital are three patients. In another room, there is a single patient. If Anna does nothing the fumes will rise up into the room containing the three patients and cause their deaths. The only way to avoid the deaths of these patients is to hit a certain switch, which will cause the fumes to bypass the room containing the three patients. As a result of doing this, the fumes will enter the room containing the single patient, causing his death. Anna decides to not hit the switch and lets three patients die.",
        "subject": "Anna's",
        "low_rating_framework": "utilitarian",
    },
    # Impersonal - Action
    {
        "code": "Data_Breach",
        "author": "greene",
        "category": "impersonal",
        "dilemma_type": "action",
        "researcher": "G",
        "text": "Oliver is a management consultant working on a case for a large corporate client. He has access to confidential information that would be very useful to investors. Oliver has a friend who plays the stock market. He owes this friend a sizable sum of money. By providing her with certain confidential information he could help her make a lot of money, considerably more than he owes her. If Oliver did this, she would insist on canceling his debt. Releasing information in this way is strictly forbidden by federal law. Oliver decides to provide her the confidetial information.",
        "subject": "Oliver's",
        "low_rating_framework": "deontological",
    },
]

# Koerner base dilemmas and their variations
# Each base dilemma has 4 variations:
# - BG-Prohibition: BenefitsGreater, Prohibition (action is prohibited)
# - BS-Prohibition: BenefitsSmaller, Prohibition (action is prohibited)
# - BG-Prescription: BenefitsGreater, Prescription (action is prescribed)
# - BS-Prescription: BenefitsSmaller, Prescription (action is prescribed)

KOERNER_BASE_DILEMMAS = {
    "Abduction": {
        "researcher": "K",
        "subject": "José's",
        "base_scenario": "José is the president of a country. A guerrilla group operating in a conflict zone has abducted a journalist from his country and threatens to behead him if José's government does not pay a ransom of one million dollars. ",
    },
    "Vaccine": {
        "researcher": "K",
        "subject": "Nina's",
        "base_scenario": "Nina is the director of a hospital in a developing country. A foreign student who is volunteering in the country got infected with a rare virus.",
    },
    "Construction_Site": {
        "researcher": "K",
        "subject": "Liam's",
        "base_scenario": "Liam is a construction worker on the construction site for a new high-rise of a wealthy and powerful investor. The man is known to increase his wealth by dubious practices. ",
    },
    "Rawanda": {
        "researcher": "K",
        "subject": "Emma's",
        "base_scenario": "Emma is the project leader of a development aid team in a foreign country when ethnic tensions start to escalate. The members of the ethnic majority persecute the members of the ethnic minority. One of Emma's minority employees arrives at the centre of the team after witnessing a colleague being killed by an armed group of majority members. Shortly afterwards, the armed group gathers in front of Emma's centre. ",
    },
}

KOERNER_VARIATIONS = {
    "bg_prohibition": {
        "label": "BenefitsGreater-Prohibition",
        "benefit_modifier": "many",
        "harm_modifier": "few",
        "action_type": "prohibition",
    },
    "bs_prohibition": {
        "label": "BenefitsSmaller-Prohibition",
        "benefit_modifier": "few",
        "harm_modifier": "many",
        "action_type": "prohibition",
    },
    "bg_prescription": {
        "label": "BenefitsGreater-Prescription",
        "benefit_modifier": "many",
        "harm_modifier": "few",
        "action_type": "prescription",
    },
    "bs_prescription": {
        "label": "BenefitsSmaller-Prescription",
        "benefit_modifier": "few",
        "harm_modifier": "many",
        "action_type": "prescription",
    },
}

# Generate full text for each Koerner variation
KOERNER_DILEMMA_TEXTS = {
    "Abduction": {
        "bg_prohibition": "José is the president of a country. A guerrilla group operating in a conflict zone has abducted a journalist from his country and threatens to behead him if José’s government does not pay a ransom of one million dollars. The group will use the ransom money to buy weapons for their guerrilla war, which will cause the deaths of many people. Congress has approved payment of the ransom, but José has the power to veto the payment. He decides to veto it.",
        "bs_prohibition": "José is the president of a country. A guerrilla group operating in a conflict zone has abducted a journalist from his country and threatens to behead him if José’s government does not pay a ransom of one million dollars. The group will use the ransom money to buy food for their families, who live in an area that has been plagued by several droughts. Congress has approved payment of the ransom, but José has the power to veto the payment. He decides to veto it.",
        "bg_prescription": "José is the president of a country. A guerrilla group operating in a conflict zone has abducted a journalist from his country and threatens to behead him if José’s government does not pay a ransom of one million dollars. The group will use the ransom money to buy food for their families, who live in an area that has been plagued by several droughts. As the president, Jose has the power to approve payment of the ransom. He decides to approve it.",
        "bs_prescription": "José is the president of a country. A guerrilla group operating in a conflict zone has abducted a journalist from his country and threatens to behead him if José’s government does not pay a ransom of one million dollars. The group will use the ransom money to buy weapons for their guerilla war, which will cause the deaths of many people. As the president, Jose has the power to approve payment of the ransom. He decides to approve it.",
    },
    "Vaccine": {
        "bg_prohibition": "Nina is the director of a hospital in a developing country. A foreign student who is volunteering in the country got infected with a rare virus. The virus is highly contagious and deadly to seniors and children. The only medication that can effectively stop the virus from spreading has severe side effects. Although the virus will not kill her, the student suffers from a chronic immune deficiency that will make her die from these side-effects. Nina decides to give the student the medication.",
        "bs_prohibition": "Nina is the director of a hospital in a developing country. A foreign student who is volunteering in the country got infected with a rare virus. The virus is highly contagious and can cause severe stomach cramps. The only medication that can effectively stop the virus from spreading has severe side effects. Although the virus will not kill her, the student suffers from a chronic immune deficiency that will make her die from these side-effects. Nina decides to give the student the medication.",
        "bg_prescription": "Nina is the director of a hospital in a developing country. A foreign student who is volunteering in the country got infected with a rare virus. The virus is highly contagious and can cause severe stomach cramps. The student suffers from a chronic immune deficiency that will make her die from the virus if she is not returned to her home country for special treatment. However, taking her out of quarantine involves a considerable risk that the virus will spread. Nina decides to take the student out of quarantine to return her to her home country for treatment.",
        "bs_prescription": "Nina is the director of a hospital in a developing country. A foreign student who is volunteering in the country got infected with a rare virus. The virus is highly contagious and deadly to seniors and children. The student suffers from a chronic immune deficiency that will make her die from the virus if she is not returned to her home country for special treatment. However, taking her out of quarantine involves a considerable risk that the virus will spread. Nina decides to take the student out of quarantine to return her to her home country for treatment.",
    },
    "Construction_Site": {
        "bg_prohibition": "Liam is a construction worker on the construction site for a new high-rise of a wealthy and powerful investor. The man is known to increase his wealth by dubious practices. Specifically, he is hiring people to set buildings on fire so that he can evict tenants and convert the buildings into luxury properties. In several cases, tenants were seriously injured or killed, but prosecutors have been unable to convict him. While Liam and the man are on top of the building, Liam sees an opportunity to shove him off the building. The building is high enough for the man to die, which would prevent him from causing more harm to innocent tenants. No one is around to see what is happening, and his death would look like an accident. Liam decides to shove the man off the roof.",
        "bs_prohibition": "Liam is a construction worker on the construction site for a new high-rise of a wealthy and powerful investor. The man is known to increase his wealth by dubious practices. Specifically, he is bribing officials so that he can evict tenants and convert the buildings into luxury properties. In several cases, tenants were unable to find comparable alternatives, but prosecutors have been unable to convict him. While Liam and the man are on top of the building, Liam sees an opportunity to shove him off the building. The building is high enough for the man to die, which would prevent him from causing more harm to innocent tenants. No one is around to see what is happening, and his death would look like an accident. Liam decides to shove the man off the roof.",
        "bg_prescription": "Liam is a construction worker on the construction site for a new high-rise of a wealthy and powerful investor. The man is known to increase his wealth by dubious practices. Specifically, he is bribing officials so that he can evict tenants and convert the buildings into luxury properties. In several cases, tenants were unable to find comparable alternatives, but prosecutors have been unable to convict him. While Liam and the man are on top of the building, the man slips and will fall from the building unless Liam grabs him and pulls him up. The building is high enough for the man to die, which would prevent him from causing more harm to innocent tenants. No one is around to see what is happening, and his death would look like an accident. Liam decides to grab the man and save him.",
        "bs_prescription": "Liam is a construction worker on the construction site for a new high-rise of a wealthy and powerful investor. The man is known to increase his wealth by dubious practices.  Specifically, he is hiring people to set buildings on fire, so that he can evict tenants and convert the buildings into luxury properties. In several cases, tenants were seriously injured or killed, but prosecutors have been unable to convict him. While Liam and the man are on top of the building, the man slips and will fall from the building unless Liam grabs him and pulls him up. The building is high enough for the man to die, which would prevent him from causing more harm to innocent tenants. No one is around to see what is happening, and his death would look like an accident. Liam decides to grab the man and save him.",
    },
    "Rawanda": {
        "bg_prohibition": "Emma is the project leader of a development aid team in a foreign country when ethnic tensions start to escalate. The members of the ethnic majority persecute the members of the ethnic minority. One of Emma’s minority employees arrives at the centre of the team after witnessing a colleague being killed by an armed group of majority members. Shortly afterwards, the armed group gathers in front of Emma’s centre. They threaten to stop an approaching bus and kill all passengers belonging to the ethnic minority if Emma does not hand over the employee. If she hands over your employee, he will be shot and killed by the armed group. Emma decides to hand over the employee to the armed group.",
        "bs_prohibition": "Emma is the project leader of a development aid team in a foreign country when ethnic tensions start to escalate. The members of the ethnic majority persecute the members of the ethnic minority. One of Emma’s minority employees arrives at the centre of the team after witnessing a colleague being killed by an armed group of majority members. Shortly afterwards, the armed group gathers in front of Emma’s centre. They threaten to set one of her team’s cars on fire that is parked in front of the center if Emma does not hand over the employee. If she hands over her employee, he will be shot and killed by the armed group. Emma decides to hand over the employee to the armed group.",
        "bg_prescription": "Emma is the project leader of a development aid team in a foreign country when ethnic tensions start to escalate. The members of the ethnic majority persecute the members of the ethnic minority. One of Emma’s minority employees arrives at the centre of the team after witnessing a colleague being killed by an armed group of majority members. Shortly afterwards, the armed group gathers in front of Emma’s centre. They threaten to set one of her team’s cars on fire that is parked in front of the center if Emma does not hand over the employee. If she hands over her employee, he will be shot and killed by the armed group. Emma knows of a secret tunnel at her center that would allow her employee to flee without being harmed. Emma lets her employee flee through the tunnel.",
        "bs_prescription": "Emma is the project leader of a development aid team in a foreign country when ethnic tensions start to escalate. The members of the ethnic majority persecute the members of the ethnic minority. One of Emma’s minority employees arrives at the centre of the team after witnessing a colleague being killed by an armed group of majority members. Shortly afterwards, the armed group gathers in front of Emma’s centre. They threaten to stop an approaching bus and kill all passengers belonging to the ethnic minority if she does not hand over the employee. If she hands over her employee, he will be shot and killed by the armed group. Emma knows of a secret tunnel at her center that would allow her employee to flee without being harmed. Emma lets her employee flee through the tunnel."
    },
}


def generate_koerner_dilemmas():
    """Generate all 16 Koerner dilemma variations."""
    dilemmas = []

    for base_code, base_info in KOERNER_BASE_DILEMMAS.items():
        for var_code, var_info in KOERNER_VARIATIONS.items():
            dilemma_code = f"{base_code}_{var_code}"
            text = KOERNER_DILEMMA_TEXTS[base_code][var_code]

            # Framework depends on variation type:
            # - prohibition: low rating = deontological (action is wrong)
            # - prescription: low rating = utilitarian (inaction is wrong)
            if var_info["action_type"] == "prohibition":
                low_framework = "deontological"
            else:
                low_framework = "utilitarian"

            dilemmas.append({
                "code": dilemma_code,
                "author": "koerner",
                "category": "koerner",
                "dilemma_type": "action" if var_info["action_type"] == "prohibition" else "omission",
                "researcher": base_info["researcher"],
                "text": text,
                "subject": base_info["subject"],
                "low_rating_framework": low_framework,
                "variation_type": var_code,
                "base_dilemma_code": base_code,
            })

    return dilemmas


class Command(BaseCommand):
    help = 'Load moral dilemmas into the database (22 total: 6 Greene + 16 Koerner variations)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing dilemmas before loading',
        )

    def handle(self, *args, **options):
        if options['clear']:
            deleted_count, _ = Dilemma.objects.all().delete()
            self.stdout.write(f'Deleted {deleted_count} existing dilemmas')

        # Combine all dilemmas
        all_dilemmas = GREENE_DILEMMAS + generate_koerner_dilemmas()

        created_count = 0
        updated_count = 0

        for dilemma_data in all_dilemmas:
            dilemma, created = Dilemma.objects.update_or_create(
                code=dilemma_data['code'],
                defaults={
                    'author': dilemma_data.get('author', 'greene'),
                    'category': dilemma_data.get('category', 'personal'),
                    'researcher': dilemma_data.get('researcher', ''),
                    'text': dilemma_data['text'].strip(),
                    'dilemma_type': dilemma_data.get('dilemma_type', ''),
                    'subject': dilemma_data.get('subject', ''),
                    'low_rating_framework': dilemma_data.get('low_rating_framework', 'deontological'),
                    'deontological_position': dilemma_data.get('deontological_position', ''),
                    'utilitarian_position': dilemma_data.get('utilitarian_position', ''),
                    'variation_type': dilemma_data.get('variation_type', ''),
                    'base_dilemma_code': dilemma_data.get('base_dilemma_code', ''),
                }
            )

            if created:
                created_count += 1
                self.stdout.write(f'  Created: {dilemma.code}')
            else:
                updated_count += 1
                self.stdout.write(f'  Updated: {dilemma.code}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully loaded dilemmas: {created_count} created, {updated_count} updated'
            )
        )

        # Initialize 6 StanceCombination records
        self.stdout.write('\nInitializing StanceCombination records...')
        for i in range(1, 7):
            combo, created = StanceCombination.objects.get_or_create(
                combination_index=i,
                defaults={'usage_count': 0}
            )
            if created:
                self.stdout.write(f'  Created: StanceCombination {i}')
            else:
                self.stdout.write(f'  Already exists: StanceCombination {i} (usage_count={combo.usage_count})')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nTotal: {len(all_dilemmas)} dilemmas loaded, 6 stance combinations ready'
            )
        )
