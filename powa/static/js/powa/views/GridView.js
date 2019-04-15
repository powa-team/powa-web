define([
        'jquery',
        'foundation/foundation.tooltip',
        'backbone',
        'powa/views/WidgetView',
        'powa/models/Grid',
        'backgrid',
        'moment',
        'tpl!powa/templates/grid.html',
        'powa/utils/size',
        'highlight',
        'powa/utils/timeurls',
        'file-saver',
        'powa/utils/duration',
        'backgrid-filter',
        'backgrid-paginator'],
        function(jquery, foundation, Backbone, WidgetView, Grid, Backgrid, moment, template,
            size, highlight, timeurls, FileSaver){


    var DurationFormatter = {
        fromRaw: function(rawData){
            return moment(parseFloat(rawData, 10)).preciseDiff(moment(0), true);
        }
    };

    var BaseCell = Backgrid.Cell.extend({
        initialize: function(options){
            BaseCell.__super__.initialize.apply(this, arguments);
           var innerCell = $("<div>");
           var cellClass = Backgrid.resolveNameToClass(this.cell || "string", "Cell");
           this.cell = new cellClass($.extend({}, options, {$el: innerCell, tagName: "div"}));
        },

        render: function(){
            var cell = this.cell.render(),
                model = this.model,
                base = this.$el;
            if(this.column.get("url_attr")){
                var params = timeurls.parseUrl(window.location.search);
                base = $("<a>").attr("data-url-has-params", "").attr("href", model.get(this.column.get("url_attr")));
                base.get(0).search = $.param(params, true);
                this.$el.append(base);
            }
            base.append(cell.$el);
            return this;
        }
    });

    var ComposedHeader = Backgrid.Header.extend({
        initialize: function(options) {
            this.toprow = options.toprow;
            this.columns = options.columns;
            if(this.toprow){
                this.toprow = new Backbone.Collection(options.toprow);
                var i = 0;
            }
            ComposedHeader.__super__.initialize.apply(this, arguments);
        },

        render: function () {
            if(this.toprow){
                var tr = $("<tr>", {'class': 'toprow'});
                this.toprow.each(function(col){
                    var cell = $("<th>")
                            .attr("colspan",  col.get("colspan") || 1)
                            .append(
                                    $("<span>")
                                    .attr("title", col.get("name"))
                                    .html(col.get("name")));
                    cell.addClass("renderable");
                    if(col.get("merge")){
                        cell.addClass("merge");
                    }
                    tr.append(cell);
                });
                this.$el.append(tr);
            }
            this.$el.append(this.row.render().$el);
            return this;
        }
    });

    Backgrid.Extension.HtmlCell = Backgrid.Cell.extend({
        className: "html",
        render: function(){
            this.$el.empty();
            var model = this.model,
            raw_value = model.get(this.column.get("name")),
            value = raw_value.replace(/^\s+/g,"").replace(/\n\s+/, "\n");
            this.$el.append(value);
            this.delegateEvents();
            return this;
        }
    });

    Backgrid.Extension.DurationCell = Backgrid.Cell.extend({
        className: "duration-cell",
        formatter: DurationFormatter
    });
    Backgrid.Extension.BoolCell = Backgrid.Cell.extend({
        className: "boolean-cell",
        render: function() {
          this.$el.empty();

          raw = this.model.get(this.column.get('name'));
          if (raw === undefined || raw === null)
            this.$el.html('<i class="fi-prohibited"></i>');
          else if (raw)
            this.$el.html('<i class="fi-check ok"></i>');
          else
            this.$el.html('<i class="fi-x ko"></i>');

          return this;
        }
    });
    Backgrid.Extension.SizeCell = Backgrid.Cell.extend({
        className: "size-cell",
        formatter: size.SizeFormatter
    });

    Backgrid.Extension.SizerateCell = Backgrid.Cell.extend({
        className: "sizerate-cell",
        formatter: new size.SizeFormatter({suffix: 'ps'})
    });

    Backgrid.Extension.QueryCell= Backgrid.Cell.extend({
        className: "query-cell",
        render: function(){
            this.$el.empty();
            var model = this.model,
                raw_value = model.get(this.column.get("name")),
                value = raw_value.replace(/^\s+/g,"").replace(/\n\s*/g, " "),
                max_length = this.column.get("max_length"),
                too_long = value.length > max_length,
                truncated_value = too_long ? value.substring(0, max_length) + '…' : value;
                code_elem = $("<pre>").addClass("has-tip").addClass("tip-top").attr("data-tooltip", "")
                            .html(highlight.highlight("sql", truncated_value, true).value),
                base = this.$el;
            if(value === undefined){
                return this;
            }
            base.append(code_elem);
            code_elem.attr("title", "<pre>" + highlight.highlight("sql", raw_value, true).value + "</pre>");
            this.$el.foundation('tooltip', 'reflow');
            this.delegateEvents();
            return this;
        }
    });

    Backgrid.Extension.TextCell = Backgrid.Cell.extend({
        className: "text-cell"
    });

    var DescHeaderCell = Backgrid.HeaderCell.extend({
        onClick: function(e){
            e.preventDefault();
            var column = this.column;
            var collection = this.collection;
            var event = "backgrid:sort";
            var sortable = Backgrid.callByNeed(column.sortable(), column, this.collection);
            if(sortable){
                if (column.get("direction") === "descending") collection.trigger(event, column, "ascending");
                else collection.trigger(event, column, "descending");
            }
        },
        initialize: function(options) {
          /*
           * Custom header cell to get the same alignment as in underlying cells.
           */
          DescHeaderCell.__super__.initialize.apply(this, arguments);
          // first get the cell type
          // Note that we use BaseCell which has a 'cell' property
          var cell = this.column.get('cell').prototype.cell;
          // then get the className for the cell class
          var cellClass = Backgrid.resolveNameToClass(cell || "string", "Cell");
          var className = cellClass.prototype.className;
          // finally apply the className as other cells in the column
          this.$el.addClass(className);
        }
    });

    return WidgetView.extend({
            template: template,
            tag: "div",
            model: Grid,
            typname: "grid",

            events: {
                "click .export_csv a": "exportCsv"
            },

            initialize: function(){
                var self = this;
                this.grid = new Backgrid.Grid({
                    columns: this.getColumnDefinitions(),
                    collection: this.model.get("collection"),
                    header: ComposedHeader,
                    toprow: this.model.get("toprow")
                });
                this
                this.grid.body.emptyText = "No data";
                this.filter = new Backgrid.Extension.ClientSideFilter({
                      collection: this.model.get("collection")
                });
                this.paginator = new Backgrid.Extension.Paginator({
                      collection: this.model.get("collection")
                });

                this.listenTo(this.model, "widget:needrefresh", this.update);
                this.listenTo(this.model, "widget:dataload-failed", this.fail);
            },

            exportCsv: function(){
                var jscols = _.pluck(this.grid.columns.models, "attributes"),
                    columns = _.indexBy(jscols, "name"),
                    labels = _.pluck(jscols, 'label'),
                    keys = _.pluck(jscols, 'name');

                var csv = labels.join(',') + '\n';
                csv += this.model.get("collection").fullCollection.map(function(item) {
                    return _.map(keys, function(key) {
                        var cell = columns[key].cell,
                        formatter = cell.prototype && cell.prototype.formatter;
                        value = formatter && formatter.fromRaw ?
                                    formatter.fromRaw(item.get(key), item) : item.get(key);
                        value = value.toString();
                        if(value.indexOf(',') != -1 || value.indexOf('\n') != -1){
                            value = value.replace(/"/g, '""');
                            value = '"' + value + '"';
                        }
                        return value;
                    }).join(',');
                }).join('\n');
                var blob = new Blob([csv], {type: "text/csv;charset=utf-8"});
                saveAs(blob, "export_powa.csv");
            },

            getColumnDefinitions: function(){
                var columns = this.model.get("columns").slice();
                this.model.get("metrics").each(function(metric){
                    columns.push($.extend({}, metric.attributes, {
                        editable: false,
                        headerCell: DescHeaderCell,
                        cell: BaseCell.extend({
                            cell: metric.get("type")
                        })
                    }));
                });
                _.each(columns, function(c){
                    if(c.cell === undefined){
                        c.cell = BaseCell.extend({
                            cell: c.type
                        });
                    }
                    if(c.editable === undefined){
                        c.editable = false;
                    }
                });
                return columns;
            },

            update: function(){
                // apply search filter when new data is received
                this.filter.search();
                this.hideload();
                this.trigger("widget:update");
            },

            render: function(){
                this.$el.html(this.template(this.model.toJSON()));
                var url = this.model.get("url");
                if (url != undefined) {
                  var title = this.model.get("title");
                  this.$el.find(".title").append('<a href="' + url + '"'
                    + 'target="_blank">'
                    + '<i class="fi-link" title="See the documentation"></i>'
                    + '</a>');
                }
                this.$el.find(".backgrid-container").append(this.grid.render().el);
                this.$el.find(".grid_filter").append(this.filter.render().el);
                this.$el.find(".grid_paginator").append(this.paginator.render().el);
                return this;
            }
        }, {});

});
