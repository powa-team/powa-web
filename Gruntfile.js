module.exports = function(grunt) {

  // Project configuration.
  grunt.initConfig({
    uglify: {
      options: {
        banner: '/*! <%= grunt.template.today("yyyy-mm-dd") %> */\n'
      },
      build: {
        src: 'powa/static/build/powa/main.js',
        dest: 'powa/static/js/powa.min-all.js'
      }
    },
    copy: {
        cssAsScss: {
            files: [
            {
                expand: true,
                cwd: 'powa/static/',
                src: ['bower_components/**/*.css', 'libs/**/*.css', '!**/*.min.css'],
                dest: 'powa/static/',
                filter: 'isFile',
                ext: ".scss"
            }
            ]
        },
        requirejs: {
            files: [
            {
                cwd: 'powa:static/',
                src: ['bower_components/requirejs/require.js'],
                dest: ['powa/static/js/'],
                filter: 'isFile'
            }
            ]
        }
    },
    requirejs: {
        all: {
            options: {
                baseUrl: "./powa/static/js",
                wrap: true,
                name: "powa/main",
                optimize: "uglify",
                uglify: {
                    "except": ["$super"]
                },
                preserveLicenseComments: false,
                generateSourceMaps: false,
                mainConfigFile: "./powa/static/js/config.js",
                out: "powa/static/js/powa.min-all.js",
            }
        }
    },

    sass: {
        all: {
            files: {
                'powa/static/css/powa-all.min.css': 'powa/static/scss/powa.scss'
            }
        }
    },

    bowerRequirejs: {
      all: {
        options: {
          baseUrl: "",
          excludeDev: true,
          transitive: true
        }
      },
      target: {
        rjsConfig: 'powa/static/js/config.js'
      }
    }
  });


  // Load the plugin that provides the "uglify" task.

  // Default task(s).
  grunt.loadNpmTasks('grunt-bower-requirejs');
  grunt.loadNpmTasks('grunt-contrib-copy');
  grunt.loadNpmTasks('grunt-contrib-requirejs');
  grunt.loadNpmTasks('grunt-contrib-uglify');
  grunt.loadNpmTasks('grunt-sass');

  grunt.registerTask('default', ['bowerRequirejs', 'copy', 'sass']);
  grunt.registerTask('dist', ['bowerRequirejs', 'copy', 'requirejs', 'sass']);

};
