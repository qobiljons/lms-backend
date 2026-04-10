                                                

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0002_subscriptionplan_is_vip_coursepurchase'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subscription',
            name='plan',
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='user',
        ),
        migrations.RemoveField(
            model_name='payment',
            name='subscription',
        ),
        migrations.DeleteModel(
            name='SubscriptionPlan',
        ),
        migrations.DeleteModel(
            name='Subscription',
        ),
    ]
