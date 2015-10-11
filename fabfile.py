from fabric.api import *

# the user to use for the remote commands
env.user = 'dev'
# the servers where the commands are executed
env.hosts = ['ssh.nikrdc.com']

# def pack():
#     # create a new source distribution as tarball
#     local('tar -cvzf devaffair.tar.gz .')

def dependencies():
    with prefix(". /usr/local/bin/virtualenvwrapper.sh; workon uberadventure"):
        run('pip install -r requirements.txt')

def deploy():
    with cd('~/devaffair'):
        run('git pull origin master')
        dependencies()

    run('touch /tmp/reload_uberadventure')
