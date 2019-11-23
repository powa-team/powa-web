define([
        'powa/views/WidgetView',
        'powa/models/Wizard',
        'tpl!powa/templates/wizard.html',
        'highlight',
        'moment',
        'backgrid',
        'backbone'],
function(WidgetView, Wizard, template, highlight, moment, Backgrid, Backbone){


    var h = "500",
        w = "200"; // Default width, then overriden by what the dashboard layout set.

    return WidgetView.extend({
        model: Wizard,
        template: template,
        typname: "wizard",

        events: {
            "click .launcher": "launchOptimization"
        },

        initialize: function(args){
            this.model = args.model;
            this.listenTo(this.model, "widget:dataload-failed", this.fail);
            this.listenTo(this.model, "widget:update_progress", this.change_progress);
            this.listenTo(this.model, "wizard:start", this.onStart);
            this.listenTo(this.model, "wizard:end", this.onEnd);
            this.$el.addClass("wizard-widget");
            this.indexgrid = new Backgrid.Grid({
                columns: [{
                    editable: false,
                    name: "ddl",
                    label: "Index",
                    cell: "query"
                },{
                    editable: false,
                    name: "quals",
                    label: "Used by",
                    cell: "html",
                },{
                    editable: false,
                    name: "nbqueries",
                    label: "# Queries boosted",
                    cell: "string"
                }],
                emptyText: "No qual to optimize !",
                collection: this.model.get("indexes")
            });
            this.indexcheckerrorgrid = new Backgrid.Grid({
                columns: [{
                    editable: false,
                    name: "ddl",
                    label: "Hypothetical index creation error",
                    cell: "query"
                },{
                    editable: false,
                    name: "error",
                    label: "Reason",
                    cell: "string",
                }],
              emptyText: "No hypothetical index creation error.",
              collection: this.model.get("indexescheckserror")
            });
            this.indexcheckgrid = new Backgrid.Grid({
                columns: [{
                    editable: false,
                    name: "query",
                    label: "Query",
                    cell: "query"
                },{
                    editable: false,
                    name: "used",
                    label: "Index used",
                    cell: "bool",
                },{
                    editable: false,
                    name: "gain",
                    label: "Gain",
                    cell: "string"
                }],
              emptyText: "No index validation done.",
              collection: this.model.get("indexeschecks")
            });
            this.unoptimizablegrid = new Backgrid.Grid({
                columns: [{
                    editable: false,
                    name: "repr",
                    label: "Unoptimized quals",
                    cell: "html"
                }],
                emptyText: "All quals could be optimized.",
                collection: this.model.get("unoptimizable")
            });
            this.render();
        },



        change_progress: function(state, progress){
            this.$progress_label.text(state);
            this.$progress_elem.css({width: progress + "%"});
        },

        onStart: function(state, progress){
            this.$el.find(".summary").show();
            this.$el.find(".launcher").prop("disabled", true);
            this.$gridel.show();
            this.$gridel2.show();
            this.$gridel3.show();
            this.$unoptimizedGrid.show();
        },

        onEnd: function(state, progress){
            this.$el.find(".launcher").prop("disabled", false);
        },

        showload: function(){

        },

        render: function(){
            var self = this;
            if (!this.model.get("has_remote_conn")) {
                this.$el.html('<h4>' + this.model.get("title") + '</h4>' +
                        '<span>Impossible to suggest indexes: impossible ' +
                        ' to connect to the remote database. <br />' +
                        '<b>' + this.model.get("conn_error") + '</b>' +
                        '</span>');
                return this;
            }
            if (!this.model.get("has_qualstats")) {
                this.$el.html('<h4>' + this.model.get("title") + '</h4>' +
                        '<span>Impossible to suggest indexes: please ' +
                        ' enable support for pg_qualstats in powa or update ' +
                        ' pg_qualstats extension to a newer version. ' +
                        ' See <a href="http://powa.readthedocs.io"> ' +
                        ' the documentation for more information</span>');
                return this;
            }
            this.$el.html(this.template(this.model.toJSON()));
            this.$el.find(".unoptimizablegrid").hide();
            this.$el.find(".indexesgrid").hide();
            this.$el.find(".indexescheckserrorgrid").hide();
            this.$el.find(".indexeschecksgrid").hide();
            this.$el.find(".summary").hide();
            this.$el.find(".results").hide();
            this.$progress_elem = this.$el.find(".progress");
            this.$progress_label = this.$el.find(".progress_label");
            this.$unoptimizedGrid = this.$el.find(".unoptimizablegrid");
            this.$unoptimizedGrid.append(this.unoptimizablegrid.render().el);
            this.$gridel = this.$el.find(".indexesgrid");
            this.$gridel.append(this.indexgrid.render().el);
            this.$gridel2 = this.$el.find(".indexescheckserrorgrid");
            this.$gridel2.append(this.indexcheckerrorgrid.render().el);
            this.$gridel3 = this.$el.find(".indexeschecksgrid");
            this.$gridel3.append(this.indexcheckgrid.render().el);
            return this;
        },

        resolve_indexes: function(path){
            var self = this;
            this.change_progress("Collecting index suggestion", 0);
            var interesting_links = _.filter(path, function(link){
                return link.value != 0;
            });
            _.each(interesting_links , function(link, index){
                self.change_progress("Collecting index suggestion", index / interesting_links.length);
            });
        },

        launchOptimization: function(){
            this.model.launchOptimization({
                from_date: this.from_date,
                to_date: this.to_date
            });
        },

        updateIndexList: function(){
        }

    });
});
