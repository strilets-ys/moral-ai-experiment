from django.core.management.base import BaseCommand
from experiment.models import Dilemma


DILEMMAS = [
    {
        "type": "action",
        "name": "Tyrannicide",
        "researcher": "K",
        "scenario": "José an army officer in the Dominican Republic in 1961. For decades now, his country is governed by the dictator Rafael Trujillo who has had thousands of people killed because of their ethnicity or their political views. José is a member of a group that wants a new start for your country without a civil war. To achieve this goal, they consider it unavoidable to kill the dictator in order to disempower him, his family, and his followers. For this, José and six co–conspirators are asked to ambush and kill the dictator. If they kill the dictator, their country will have a chance for a new start. If they do not kill him, the regime will continue its killings. José decides to kill the dictator.",
        "subject": "José's",
        "low_rating_framework": "deontological",  # 1=killing is wrong, 7=utilitarian sacrifice
    },
    {
        "type": "omission",
        "name": "Medicine costs",
        "researcher": "K",
        "scenario": "Anna is a Belgian minister of health. A 7–year–old boy who suffers from a very rare immunological disease asks her for a refund for his medicine. Without taking this medicine regularly, the boy will die. Currently, the medicine is not covered by the health care system, and it is so expensive that the family, who has been buying the medicine for years, will not be able to raise enough money for much longer (approximately 200,000 euros per year). Thus, the boy will die, if Anna refuses the refund. If she refuses to pay for the medicine, the boy will probably die within the next few years. However, if she pays, this money will have to be saved elsewhere; thus, other treatments will not be able to be covered. Funding the boy will therefore likely lead to the death of several other people. Anna decides to not refund the money.",
        "subject": "Anna's",
        "low_rating_framework": "deontological",  # 1=duty to save child, 7=utilitarian greater good
    },
    {
        "type": "omission",
        "name": "Rugby cannibalism",
        "researcher": "K",
        "scenario": "Mateo is a member of a rugby team flying from Montevideo to Santiago de Chile in 1972. The plane crashes, killing 15 of the 40 people on board. The survivors are in an inaccessible region and have no means of communication. However, they do have a radio. They are now at an altitude of 13,000 feet/4,000 meters at –20°F/–30°C. After ten days, only 19 of you the survivors are still alive, they have no food left and they hear on the radio that the search for your plane has been given up. Mateo and the others are contemplating whether to eat the remains of your dead team mates, violating their dignity and peace of the dead. If Mateo and the rest of the survivors eat human bodies, they will survive longer and increase your chances of being rescued. If Mateo and the others do not eat dead bodies, they will starve to death soon. Mateo persuades the others to not eat the dead bodies.",
        "subject": "Mateo's",
        "low_rating_framework": "utilitarian",  # 1=should eat to survive, 7=deontological respect for dead
    },
    {
        "type": "action",
        "name": "Endowment",
        "researcher": "K",
        "scenario": "After a long–term imprisonment, a convicted child kidnapper and murderer wants to organize a foundation for young victims of crime. Ella is the president of the agency who decides about the foundation. The founder would offer a seed capital of 25,000 euros. However, the foundation would be named after the offender and it is unclear whether he is acting out of remorse or simply to clear his name. The family of his victim opposes such a foundation and considers it immoral, derogatory, and an exploitation of the victim. If Ella opposes the foundation, the capital will be lost. If she approves the foundation, crime victims can be helped by the starting capital and additional fund raisings. Ella decides to oppose the foundation.",
        "subject": "Ella's",
        "low_rating_framework": "utilitarian",  # 1=take money to help victims, 7=deontological respect family
    },
    {
        "type": "action",
        "name": "Marital Affair",
        "researcher": "E",
        "scenario": "Nina is a good friend of Martin, who is married to Linda. One day Nina discovers that Linda is having a love affair with another man for one year. It is clear that Linda does not want to leave Martin or tell him the truth, but wishes the affair to continue secretly. Nina knows that for Martin it is important that Linda and him are faithful to each other and do not sleep with anyone else. Nina also knows that Martin would leave Linda if he discovers that she has been lying to him. Nina decides to tell Martin that Linda has an affair. Martin and Linda get a divorce.",
        "subject": "Nina's",
        "low_rating_framework": "utilitarian",  # 1=don't interfere/avoid harm, 7=deontological honesty
        # LLM-only context (not shown to participant):
        "utilitarian_position": "Nina should NOT have told Martin - her revelation destroyed a marriage and caused harm that could have been avoided.",
        "deontological_position": "Nina was RIGHT to tell Martin - honesty is a duty and Martin deserved the truth.",
    },
    {
        "type": "action",
        "name": "Terrorist Negotiation",
        "researcher": "G",
        "scenario": "Emilia is negotiating with a powerful and determined terrorist who is about to set off a bomb in a crowded area. Her advantage is that she has his innocent teenage son in her custody. There is only one thing that she can do to stop him from detonating his bomb, which will kill thousands of people if detonated. To stop him, she must contact him over the satellite hook-up that she has established and, in front of the camera, she breaks one of his son's arms and then threatens to break the other one if he does not give himself up. Emilia accepts to do this action.",
        "subject": "Emilia's",
        "low_rating_framework": "deontological",  # 1=torture is wrong, 7=utilitarian save thousands
    },
    {
        "type": "omission",
        "name": "Crew Killing",
        "researcher": "G",
        "scenario": "Azzo is the captain of a military submarine travelling underneath a large iceberg. An on-board explosion has caused him to lose a large part of the oxygen supply and has injured one of his crew who is quickly losing blood. The injured crew member is going to die from his wounds no matter what happens. The remaining oxygen supply is not sufficient for the entire crew to make it to the surface. The only way to save the other crew members is to shoot dead the injured crew member so that there will be just enough oxygen for the rest of the crew to survive. Azzo decides to not kill the fatally injured crew member.",
        "subject": "Azzo's",
        "low_rating_framework": "utilitarian",  # 1=kill one to save many, 7=deontological don't kill
    },
    {
        "type": "action",
        "name": "Hospital Fumes",
        "researcher": "G",
        "scenario": "Ann is the late-nightwatch nurse in a hospital. Due to an accident in the building next door, there are deadly fumes rising up through the hospital's ventilation system. In a certain room of the hospital are three patients. In another room, there is a single patient. If Anna does nothing the fumes will rise up into the room containing the three patients and cause their deaths. The only way to avoid the deaths of these patients is to hit a certain switch, which will cause the fumes to bypass the room containing the three patients. As a result of doing this, the fumes will enter the room containing the single patient, causing his death. Anna decides to hit the switch to kill this patient.",
        "subject": "Anna's",
        "low_rating_framework": "deontological",  # 1=don't actively kill, 7=utilitarian save three
    },
]


class Command(BaseCommand):
    help = 'Load moral dilemmas into the database'

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

        created_count = 0
        updated_count = 0

        for dilemma_data in DILEMMAS:
            dilemma, created = Dilemma.objects.update_or_create(
                code=dilemma_data['name'],
                defaults={
                    'researcher': dilemma_data.get('researcher', ''),
                    'text': dilemma_data['scenario'].strip(),
                    'dilemma_type': dilemma_data['type'],
                    'subject': dilemma_data.get('subject', ''),
                    'low_rating_framework': dilemma_data.get('low_rating_framework', 'deontological'),
                    'deontological_position': dilemma_data.get('deontological_position', ''),
                    'utilitarian_position': dilemma_data.get('utilitarian_position', ''),
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
