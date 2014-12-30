define([
        'jquery',
        'foundation',
        'backbone',
        'powa/views/WidgetView',
        'powa/models/Grid',
        'backgrid',
        'moment',
        'tpl!powa/templates/grid.html',
        'powa/utils/size',
        'highlight',
        'powa/utils/duration',
        'backgrid-filter',
        'backgrid-paginator'],
        function(jquery, foundation, Backbone, WidgetView, Grid, Backgrid, moment, template, size, highlight){

    var DurationFormatter = {
        fromRaw: function(rawData){
            return moment(parseInt(rawData, 10)).preciseDiff(moment(0));
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
                base = $("<a>").attr("href", model.get(this.column.get("url_attr")));
                this.$el.append(base);
            }
            base.append(cell.$el);
            return this;
        }
    });

    Backgrid.Extension.DurationCell = Backgrid.Cell.extend({
        className: "duration",
        formatter: DurationFormatter
    });
    Backgrid.Extension.SizeCell = Backgrid.Cell.extend({
        className: "size",
        formatter: size.SizeFormatter
    });

    Backgrid.Extension.SizerateCell = Backgrid.Cell.extend({
        className: "sizerate",
        formatter: new size.SizeFormatter({suffix: 'ps'})
    });

    Backgrid.Extension.QueryCell= Backgrid.Cell.extend({
        className: "query",
        render: function(){
            this.$el.empty();
            var model = this.model,
                raw_value = model.get(this.column.get("name")),
                value = raw_value.replace(/^\s+/g,"").replace(/\n\s+/, "\n"),
                max_length = this.column.get("max_length"),
                truncated_value = max_length ? value.substring(0, max_length) : value;
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

    return WidgetView.extend({
            template: template,
            tag: "div",
            model: Grid,

            initialize: function(){
                var self = this;
                this.grid = new Backgrid.Grid({
                    columns: this.getColumnDefinitions(),
                    collection: this.model.get("collection"),
                });
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

            getColumnDefinitions: function(){
                var columns = this.model.get("columns");
                this.model.get("metrics").each(function(metric){
                    columns.push($.extend({}, metric.attributes, {
                        editable: false,
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
                this.hideload();
                this.trigger("widget:update");
            },

            render: function(){
                this.$el.html(this.template(this.model.toJSON()));
                this.$el.find(".backgrid-container").append(this.grid.render().el);
                this.$el.find(".grid_filter").append(this.filter.render().el);
                this.$el.find(".grid_paginator").append(this.paginator.render().el);
                return this;
            }
        });

});
