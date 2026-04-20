from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Create user groups for project management system'
    
    def handle(self, *args, **options):
        """
        Create project_supervisor and production_staff groups
        """
        
        # Create project_supervisor group
        supervisor_group, created = Group.objects.get_or_create(name='project_supervisor')
        if created:
            self.stdout.write(
                self.style.SUCCESS('✅ Created group: project_supervisor')
            )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️  Group already exists: project_supervisor')
            )
        
        # Create production_staff group
        production_group, created = Group.objects.get_or_create(name='production_staff')
        if created:
            self.stdout.write(
                self.style.SUCCESS('✅ Created group: production_staff')
            )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️  Group already exists: production_staff')
            )
        
        self.stdout.write(
            self.style.SUCCESS('\n✨ Group setup complete!\n')
        )
        self.stdout.write(
            'Next steps:\n'
            '1. Go to http://localhost:8000/admin/auth/user/\n'
            '2. Select your user\n'
            '3. Under "Groups", add them to:\n'
            '   - "project_supervisor" (to see project supervisor dashboard)\n'
            '   - "production_staff" (to see production room dashboard)\n'
            '4. Save the user\n'
        )
