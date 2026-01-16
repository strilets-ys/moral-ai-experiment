from django.core.management.base import BaseCommand
from experiment.models import Dilemma


# Sample moral dilemmas (based on classic trolley-problem style scenarios)
# Replace these with your actual research dilemmas
DILEMMAS = [
    {
        'code': 'trolley_switch',
        'text': '''A runaway trolley is heading toward five workers on the track who cannot escape.
You are standing next to a switch that can divert the trolley to a side track where only one worker is present.
If you pull the switch, the trolley will kill the one worker but spare the five.
Is it morally acceptable to pull the switch?'''
    },
    {
        'code': 'trolley_push',
        'text': '''A runaway trolley is heading toward five workers on the track.
You are standing on a footbridge above the tracks next to a large stranger.
The only way to stop the trolley is to push the stranger off the bridge onto the tracks below.
His body would stop the trolley, killing him but saving the five workers.
Is it morally acceptable to push the stranger?'''
    },
    {
        'code': 'transplant',
        'text': '''You are a doctor with five patients who will die without organ transplants.
A healthy patient comes in for a routine checkup. You could kill this patient and harvest their organs to save the five dying patients.
No one would ever know.
Is it morally acceptable to kill the healthy patient to save the five?'''
    },
    {
        'code': 'crying_baby',
        'text': '''During wartime, you and others are hiding from enemy soldiers in a basement.
Your baby starts to cry, and if you don't silence the baby, the soldiers will find and kill everyone hiding.
The only way to silence the baby is to smother it.
Is it morally acceptable to smother your baby to save the group?'''
    },
    {
        'code': 'lifeboat',
        'text': '''After a shipwreck, you and 30 others are in a lifeboat designed for 7 people.
The boat is sinking and everyone will drown unless the load is lightened.
You could throw some passengers overboard to save the majority.
Is it morally acceptable to throw some passengers overboard?'''
    },
    {
        'code': 'torture',
        'text': '''A terrorist has planted a bomb that will kill thousands of people.
The terrorist has been captured but refuses to reveal the bomb's location.
The only way to get the information in time is to torture the terrorist.
Is it morally acceptable to torture the terrorist to save thousands of lives?'''
    },
    {
        'code': 'vaccine',
        'text': '''A deadly pandemic is spreading rapidly. Scientists have developed a vaccine, but testing it properly would take months during which millions would die.
The vaccine could be released immediately but might have unknown side effects that could harm some recipients.
Is it morally acceptable to release the untested vaccine?'''
    },
    {
        'code': 'autonomous_car',
        'text': '''An autonomous vehicle's brakes fail while carrying one passenger.
It can either continue straight, killing five pedestrians, or swerve, killing the passenger but saving the pedestrians.
The car must be programmed to make this decision in advance.
Is it morally acceptable to program the car to swerve (sacrificing the passenger)?'''
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
                code=dilemma_data['code'],
                defaults={'text': dilemma_data['text'].strip()}
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
