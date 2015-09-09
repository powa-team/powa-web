define([
        'powa/views/WidgetView',
        'powa/models/Wizard',
        'tpl!powa/templates/wizard.html',
        'highlight',
        'moment',
        'd3',
        'backgrid',
        'backbone'],
function(WidgetView, Wizard, template, highlight, moment, d3, Backgrid, Backbone){


    var h = "500",
        w = "200"; // Default width, then overriden by what the dashboard layout set.

    return WidgetView.extend({
        model: Wizard,
        template: template,

        initialize: function(args){
            this.model = args.model;
            this.listenTo(this.model, "widget:dataload-failed", this.fail);
            this.listenTo(this.model, "widget:update_progress", this.change_progress);
            this.listenTo(this.model, "wizard:update_graph", this.update_graph);
            this.listenTo(this.model, "wizard:solved", this.display_solution);
            this.$el.addClass("wizard-widget");
            this.render();
        },



        change_progress: function(state, progress){
            this.$progress_label.text(state);
            this.$progress_elem.css({width: "[100 - " + progress + "]%"});
        },

        showload: function(){

        },

        render: function(){
            var self = this;
            this.$el.html(this.template(this.model.toJSON()));
            this.$progress_elem = this.$el.find(".progress");
            this.$progress_label = this.$el.find(".progress_label");
            this.$viselem = this.$el.find(".graph_visualisation");
            this.vis = d3.select(this.$viselem.get(0))
                .append("svg:svg")
                .attr("width", "100%")
                .attr("height", h);
            this.force = d3.layout.force()
                .nodes(this.model.get("nodes"))
                .gravity(1)
                .linkDistance(function(link) {
                    var base = link.samerel ? 0 : w / 10;
                    return base + link.value;
                })
                .charge(-30)
                .linkStrength(function(x) {
				return 10;
			    });
			this.labelforce = d3.layout.force()
                .nodes([ ])
                .gravity(0)
                .linkDistance(0)
                .linkStrength(8)
                .charge(-30);
            var updateNode = function() {
				this.attr("transform", function(d) {
					return "translate(" + d.x + "," + d.y + ")";
				});

			}
            this.node = this.vis.selectAll("g.node");
            this.anchorNode = this.vis.selectAll("g.anchorNode");
            this.anchorLink = this.vis.selectAll("line.anchorLink")

			var updateLink = function() {
				this.attr("x1", function(d) {
					return d.source.x;
				}).attr("y1", function(d) {
					return d.source.y;
				}).attr("x2", function(d) {
					return d.target.x;
				}).attr("y2", function(d) {
					return d.target.y;
				});

			}
			this.force.on("tick", function() {

				self.labelforce.start();

				self.node.call(updateNode);

				self.anchorNode.each(function(d, i) {
					if(i % 2 == 0) {
						d.x = d.node.x;
						d.y = d.node.y;
					} else {
						var b = this.childNodes[1].getBBox();

						var diffX = d.x - d.node.x;
						var diffY = d.y - d.node.y;

						var dist = Math.sqrt(diffX * diffX + diffY * diffY);

						var shiftX = b.width * (diffX - dist) / (dist * 2);
						shiftX = Math.max(-b.width, Math.min(0, shiftX));
						var shiftY = 5;
						this.childNodes[1].setAttribute("transform", "translate(" + shiftX + "," + shiftY + ")");
					}
				});


				self.anchorNode.call(updateNode);

				self.anchorLink.call(updateLink);
				self.link.call(updateLink);

			});
            return this;
        },

        update_graph: function(model){
            var nodes = model.get("nodes"),
                links = model.get("links"),
                labelanchors = [],
                shortest_path = model.get("shortest_path");
            var labellinks = [];

            w = this.$el.parent().innerWidth();

			for(var i = 0; i < nodes.length; i++) {
                /* Push twice: one will not be visible */
                var node = nodes[i];
                if(node.type == "startNode"){
                    node.x = 100;
                    node.y = h / 2;
                    node.fixed = true;
                }
                labelanchors.push({"node": nodes[i]});
                labelanchors.push({"node": nodes[i]});


                labellinks.push({
					source : i * 2,
					target : i * 2 + 1,
					weight : 1
				});

            };

            if(this.force){
                this.force.size([w, h]);
                this.force.nodes(nodes).links(links).start();
                this.node = this.vis.selectAll("g.node")
                    .data(this.force.nodes()).enter()
                    .append("svg:g")
                    .attr("class", "node");
                this.node.call(this.force.drag);
			    this.link = this.vis.selectAll("line.link")
                    .data(links).enter()
                        .append("svg:line")
                        .attr("class", "link")
                        .style("stroke", function(link){
                            if(shortest_path.indexOf(link) > -1){
                                return "red";
                            }
                            return link.value == 0 ? "#CCC" : "";
                        });
                this.node.append("svg:circle")
                    .attr("r", 5)
                    .style("fill", "#555")
                    .style("stroke", "#FFF")
                    .style("stroke-width", 3);
            }
            if(this.labelforce){
                this.labelforce.size([w, h]);
                this.labelforce.nodes(labelanchors);
                this.anchorNode = this.vis.selectAll("g.anchorNode")
                    .data(this.labelforce.nodes()).enter()
                    .append("svg:g")
                    .attr("class", "anchorNode");
                this.anchorLink = this.vis.selectAll("line.anchorLink");
                this.anchorNode.append("svg:circle")
                    .attr("r", 0)
                    .style("fill", "#FFF");
				this.anchorNode.append("svg:text")
                    .text(function(d, i) {
				        return i % 2 == 0 ? "" : d.node.label
    			    })
                    .style("fill", "#555")
                    .style("font-family", "Arial")
                    .style("font-size", 12);
                this.anchorLink.data(labellinks);
                this.labelforce.links(labellinks);
                this.labelforce.start();
            }
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

        display_solution: function(solutions){
            var grid = new Backgrid.Grid({
                columns: [
                {
                    editable: false,
                    name: "ddl",
                    cell: "query"
                }, {
                    editable: false,
                    name: "queries",
                    cell: "query",
                }, {
                    editable: false,
                    name: "quals",
                    cell: "query"
                }],
                collection: new Backbone.Collection(_.values(solutions.by_index))
            });
            this.$gridel = this.$el.find(".indexes_grid");
            this.$gridel.append(grid.render().el);
        }

    });
});
