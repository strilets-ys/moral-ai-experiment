"""
Management command to verify deployment is working correctly.
Run with: python manage.py verify_deployment
"""
from django.core.management.base import BaseCommand
from experiment.models import (
    Participant, Dilemma, DemographicsResponse, DebriefResponse,
    Rating, ChatTurn, TIPIResponse
)


class Command(BaseCommand):
    help = 'Verify that the deployment is working correctly'

    def handle(self, *args, **options):
        self.stdout.write('\n=== Deployment Verification ===\n')
        errors = []
        warnings = []

        # 1. Check models can be queried
        self.stdout.write('1. Checking database connectivity...')
        try:
            Participant.objects.count()
            self.stdout.write(self.style.SUCCESS('   ✓ Database connection OK'))
        except Exception as e:
            errors.append(f'Database error: {e}')
            self.stdout.write(self.style.ERROR(f'   ✗ Database error: {e}'))

        # 2. Check new DemographicsResponse model exists
        self.stdout.write('2. Checking DemographicsResponse model...')
        try:
            DemographicsResponse.objects.count()
            self.stdout.write(self.style.SUCCESS('   ✓ DemographicsResponse model OK'))
        except Exception as e:
            errors.append(f'DemographicsResponse model error: {e}')
            self.stdout.write(self.style.ERROR(f'   ✗ DemographicsResponse error: {e}'))

        # 3. Check Participant has new condition choices
        self.stdout.write('3. Checking Participant condition choices...')
        conditions = [c[0] for c in Participant.CONDITION_CHOICES]
        if 'persuade_demo' in conditions:
            self.stdout.write(self.style.SUCCESS('   ✓ persuade_demo condition exists'))
        else:
            errors.append('persuade_demo condition missing')
            self.stdout.write(self.style.ERROR('   ✗ persuade_demo condition missing'))

        # 4. Check Participant has demographics status
        self.stdout.write('4. Checking Participant status choices...')
        statuses = [s[0] for s in Participant.STATUS_CHOICES]
        if 'demographics' in statuses:
            self.stdout.write(self.style.SUCCESS('   ✓ demographics status exists'))
        else:
            errors.append('demographics status missing')
            self.stdout.write(self.style.ERROR('   ✗ demographics status missing'))

        # 5. Check DebriefResponse has S-TIAS fields
        self.stdout.write('5. Checking DebriefResponse S-TIAS fields...')
        debrief_fields = [f.name for f in DebriefResponse._meta.get_fields()]
        stias_fields = ['stias_confident', 'stias_reliable', 'stias_trust']
        missing = [f for f in stias_fields if f not in debrief_fields]
        if not missing:
            self.stdout.write(self.style.SUCCESS('   ✓ S-TIAS fields exist'))
        else:
            errors.append(f'Missing S-TIAS fields: {missing}')
            self.stdout.write(self.style.ERROR(f'   ✗ Missing S-TIAS fields: {missing}'))

        # 6. Check old ai_trust field is removed
        if 'ai_trust' not in debrief_fields:
            self.stdout.write(self.style.SUCCESS('   ✓ Old ai_trust field removed'))
        else:
            warnings.append('Old ai_trust field still exists')
            self.stdout.write(self.style.WARNING('   ! Old ai_trust field still exists'))

        # 7. Check dilemma counts
        self.stdout.write('6. Checking dilemma availability...')
        personal = Dilemma.objects.filter(category='personal').count()
        impersonal = Dilemma.objects.filter(category='impersonal').count()
        koerner = Dilemma.objects.filter(author='koerner').count()
        self.stdout.write(f'   Personal: {personal}, Impersonal: {impersonal}, Koerner: {koerner}')
        if personal >= 2 and impersonal >= 2 and koerner >= 4:
            self.stdout.write(self.style.SUCCESS('   ✓ Sufficient dilemmas for experiment'))
        else:
            warnings.append('May not have enough dilemmas')
            self.stdout.write(self.style.WARNING('   ! May not have enough dilemmas'))

        # 8. Data statistics
        self.stdout.write('\n7. Current data statistics:')
        stats = {
            'Participants': Participant.objects.count(),
            'Completed': Participant.objects.filter(status='complete').count(),
            'Demographics': DemographicsResponse.objects.count(),
            'TIPI': TIPIResponse.objects.count(),
            'Debrief': DebriefResponse.objects.count(),
            'Ratings': Rating.objects.count(),
            'Chat turns': ChatTurn.objects.count(),
        }
        for name, count in stats.items():
            self.stdout.write(f'   {name}: {count}')

        # 9. Check for participants without demographics (expected for old data)
        participants_without_demo = Participant.objects.filter(
            status__in=['tipi', 'pre_rating', 'chat', 'post_rating', 'debrief', 'complete']
        ).exclude(
            demographics__isnull=False
        ).count()
        if participants_without_demo > 0:
            warnings.append(f'{participants_without_demo} participants without demographics (old flow)')
            self.stdout.write(self.style.WARNING(
                f'   ! {participants_without_demo} participants without demographics (from old flow)'
            ))

        # Summary
        self.stdout.write('\n=== Summary ===')
        if errors:
            self.stdout.write(self.style.ERROR(f'ERRORS: {len(errors)}'))
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  - {e}'))
        else:
            self.stdout.write(self.style.SUCCESS('No errors found'))

        if warnings:
            self.stdout.write(self.style.WARNING(f'WARNINGS: {len(warnings)}'))
            for w in warnings:
                self.stdout.write(self.style.WARNING(f'  - {w}'))

        if not errors:
            self.stdout.write(self.style.SUCCESS('\n✓ Deployment verification PASSED\n'))
        else:
            self.stdout.write(self.style.ERROR('\n✗ Deployment verification FAILED\n'))
            return
