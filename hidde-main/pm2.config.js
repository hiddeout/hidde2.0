module.exports = {
    apps: [{
        name: 'hidde',
        script: 'main.py',
        cwd: '/root/hidde',
        interpreter: '/usr/bin/python3',
        env: {
            "PATH": process.env.PATH + ":/usr/bin"
        }
    }]
};