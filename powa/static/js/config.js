require.config({
  baseUrl: "/static/js/",
  paths: {
    backbone: "../bower_components/backbone/backbone",
    d3: "../bower_components/d3/d3.min",
    foundation: "../bower_components/foundation/js/foundation",
    modernizr: "../bower_components/modernizr/modernizr",
    "foundation-daterangepicker": "../bower_components/foundation-daterangepicker/daterangepicker",
    jquery: "../bower_components/jquery/dist/jquery.min",
    moment: "../bower_components/moment/min/moment.min",
    requirejs: "../bower_components/requirejs/require",
    "requirejs-text": "../bower_components/requirejs-text/text",
    "requirejs-tpl": "../bower_components/requirejs-tpl/tpl",
    tpl: "../bower_components/requirejs-tpl/tpl",
    rickshaw: "../bower_components/rickshaw/rickshaw.min",
    highlight: "../libs/highlight/highlight",
    underscore: "../bower_components/underscore/underscore-min",
    backgrid: "../bower_components/backgrid/lib/backgrid.min",
    spin: "../bower_components/spin.js/spin.min",
    "backgrid-filter": "../bower_components/backgrid-filter/backgrid-filter.min",
    "backgrid-paginator": "../bower_components/backgrid-paginator/backgrid-paginator.min",
    "backbone-pageable": "../bower_components/backbone-pageable/lib/backbone-pageable.min",
    "file-saver": "../bower_components/file-saver/FileSaver.min"
  },
  urlArgs: {
    date: {

    }
  },
  wrapShim: true,
  shim: {
    highlight: {
      exports: "hljs"
    },
    "foundation/foundation": {
      deps: [
        "jquery"
      ]
    },
    "foundation/foundation.tab": [
      "foundation/foundation"
    ],
    "foundation/foundation.topbar": [
      "foundation/foundation"
    ],
    "foundation/foundation.equalizer": [
      "foundation/foundation"
    ],
    "foundation/foundation.dropdown": [
      "foundation/foundation"
    ],
    "foundation/foundation.tooltip": [
      "foundation/foundation"
    ],
    "foundation/foundation.offcanvas": [
      "foundation/foundation"
    ],
    "foundation/foundation.alert": [
      "foundation/foundation"
    ],
    "foundation-daterangepicker": [
      "foundation/foundation"
    ],
    backgrid: {
      deps: [
        "jquery",
        "underscore",
        "backbone"
      ],
      exports: "Backgrid"
    },
    "backgrid-select-all": {
      deps: [
        "backgrid"
      ]
    },
    "backgrid-filter": {
      deps: [
        "backgrid"
      ]
    },
    "backgrid-paginator": {
      deps: [
        "backgrid"
      ]
    }
  },
  packages: [

  ]
});

require(["powa/main"]);
