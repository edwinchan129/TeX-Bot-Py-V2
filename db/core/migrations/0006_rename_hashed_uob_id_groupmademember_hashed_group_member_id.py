# Generated by Django 4.2.9 on 2024-01-12 17:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_rename_uobmademember_groupmademember_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='groupmademember',
            old_name='hashed_uob_id',
            new_name='hashed_group_member_id',
        ),
    ]