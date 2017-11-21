module.exports = function(grunt) {

  // Project configuration.
  grunt.initConfig({
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
                optimize: "none",
                preserveLicenseComments: false,
                generateSourceMaps: false,
                mainConfigFile: "./powa/static/js/config.js",
                out: "powa/static/js/powa.all.js"
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

  // Default task(s).
  grunt.loadNpmTasks('grunt-bower-requirejs');
  grunt.loadNpmTasks('grunt-contrib-copy');
  grunt.loadNpmTasks('grunt-contrib-requirejs');
  grunt.loadNpmTasks('grunt-sass');

  grunt.registerTask('default', ['bowerRequirejs', 'copy', 'sass']);
  grunt.registerTask('dist', ['bowerRequirejs', 'copy', 'requirejs', 'sass']);

};
