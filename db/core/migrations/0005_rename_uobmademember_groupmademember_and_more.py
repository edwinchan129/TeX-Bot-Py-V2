# Generated by Django 4.2.9 on 2024-01-12 17:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_rename_memberstrikes_discordmemberstrikes_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='UoBMadeMember',
            new_name='GroupMadeMember',
        ),
        migrations.RenameModel(
            old_name='LeftMember',
            new_name='LeftDiscordMember',
        ),
    ]