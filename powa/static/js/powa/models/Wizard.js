define(['backbone', 'powa/models/DataSourceCollection', 'jquery',
        'powa/views/GridView', 'highlight', 'powa/models/Widget'],
        function(Backbone, DataSourceCollection, $, GridView, highlight, Widget){

    var QualCollection = Backbone.Collection.extend({
        comparator: function (qual1, qual2){
            if(qual1.get("relid") != qual2.get("relid")){
                return qual1.get("relid") - qual2.get("relid")
            }
            if(qual1.get("attnum") != qual2.get("attnum")){
                return qual1.get("attnum") - qual2.get("attnum");
            }
            if(qual1.get("opno") != qual2.get("opno")){
                return qual1.get("opno") - qual2.get("opno");
            }
            return 0;
        }
    });


    var GetterModel = Backbone.Model.extend({
        get: function(attr){
            if (typeof this[attr] == 'function') {
                return this[attr]();
            }
            return Backbone.Model.prototype.get.call(this, attr);
        }
    });

    var QualModel = GetterModel.extend({

        initialize: function(values){
            this.set("quals", new QualCollection());
            this.set("contained", new NodeCollection());
            this.set("trashedQuals", new QualCollection());
            this.listenTo(this.get("quals"), "add", this.qualupdate, this);
            if(values && values.quals){
                this.get("quals").set(values.quals);
            }
        },

        qualupdate: function(newquals, options){
            if(options.internal){
                return;
            }
            var relids = _.uniq(this.get("quals").pluck("relid"));
            if(relids.length > 1){
                throw "A qual should not span more than one table";
            }
            this.set("relid", relids[0]);
            this.set("relname", this.get("quals").models[0].get("relname"));
            this.trashQuals();
        },

        relfqn: function(){
            return this.get("nspname") + "." + this.get("relname");
        },

        uniqAttnums: function(){
            return _.uniq(this.get("quals").map(function(qual){
                return qual.get("attnum");
            }));
        },

        trashQuals: function(){
            // Delete quals which do not support the most common access
            // method.
            quals = this.get("quals");
            var access_methods = {}
            quals.each(function(qual){
                _.each(_.keys(qual.get("amops")), function(am){
                    access_methods[am] = (access_methods[am] || 0) + 1;
                });
            });
            var most_common_am = _.max(_.pairs(access_methods), function(pair){
                return pair[1];
            })[0];
            var grouped = quals.groupBy(function(qual){
                return qual.get("amops")[most_common_am] ? "keep" : "trash";
            });
            this.get("trashedQuals").set(grouped.trash, {internal: true});
            this.get("quals").set(grouped.keep, {internal: true});
        },

        repr: function(){
            var base = "WHERE ",
                hasquals = this.get("quals").size() > 0;
            if(hasquals){
                base += _.uniq(this.get("quals").map(function(qual){
                    return qual.get("label")
                }, this)).join(" AND ");
            }
            base = "<pre>" + highlight.highlight("sql", base, true).value + "</pre>";
            var unmanaged = this.get("trashedQuals").map(function(qual, idx){
                var part = "<strike><pre>";
                var value = qual.get("label");
                if(idx == 0 && hasquals){
                    value = " AND " + value;
                }
                if(idx < this.get("trashedQuals").length - 1){
                    value += " AND ";
                }
                value = highlight.highlight("sql", "WHERE " + value, true).value;
                value = value.substring(value.indexOf("</span> ") + 8);
                part += value + "</pre></strike>";
                return part;
            }, this).join(" AND ");
            base = base + unmanaged;
            base = base + this.get("contained").map(function(node){
              return node.repr();
            }, this).join("");
            return base;
        },

        merge: function(node2){
            this.set("queries", _.uniq(this.get("queries").concat(node2.get("queries"))));
            this.set("queryids", _.uniq(this.get("queryids").concat(node2.get("queryids"))));
            var quals = _.union(this.get("quals").models, node2.get("quals").models);
            this.get("quals").set(quals);
        }
    });

    var IndexModel = GetterModel.extend({

        ddl: function(){
            var am = this.get("ams")[0];
            var node = this.get("node");
            var ddl = "CREATE INDEX ON " + this.get("node").get("relfqn");
            if(this.get("ams").indexOf("btree") > 0){
                // Propose btree when possible
                am = "";
            } else {
                am = " USING " + am;
            }
            ddl += am + "(";
            var myattnums = this.get("attnums");
            var attnames = _.uniq(_.map(_.sortBy(this.get("node").get("quals").map(function(qual){
                var attnum = qual.get("attnum");
                var attname = qual.get("attname");
                return [myattnums.indexOf(attnum), attname];
            }), function(pair){
                return pair[0];
            }), function(pair){return pair[1]}));
            ddl += attnames.join(",") + ")";
            return ddl;
        },

        nbqueries: function(){
            return this.get("queryids").length;
        },

        quals: function(){
            return this.get("node").get("repr");
        }
    });

    var IndexCheckErrorModel = GetterModel.extend({

        ddl: function(){
            return this.get("_ddl");
        },

        error: function(){
            return this.get("_error");
        }
    });

    var IndexCheckModel = GetterModel.extend({

        query: function(){
            return this.get("_query");
        },

        used: function(){
            return this.get("_gain") > 0;
        },

        gain: function(){
            return this.get("_gain") + "%";
        }
    });


    var NodeCollection = Backbone.Collection.extend({
        model: QualModel
    });

    var IndexCollection = Backbone.Collection.extend({
        model: IndexModel
    });

    var IndexCheckErrorCollection = Backbone.Collection.extend({
        model: IndexCheckErrorModel
    });

    var IndexCheckCollection = Backbone.Collection.extend({
        model: IndexCheckModel
    });

    var make_attrid = function(qual){
        return "" + qual.get("relid") + "/" + qual.get("attnum");
    }

    var ColumnScoringMethod = {
        scoreNode: function(node){
            return _.uniq(node.get("quals").map(function(qual){
                return qual.get("attnum");
            })).length;
        },

        scorePath: function(nodes){
            return _.reduce(nodes, function(memo, node){
                return memo + node.get("score");
            }, 0);
        }
    }

    return Widget.extend({
        typname: "wizard",
        initialize: function(){
            this.set("stage", "Starting wizard...");
            this.set("progress", 0);
            this.set("indexes", new IndexCollection());
            this.set("indexescheckserror", new IndexCheckErrorCollection());
            this.set("indexeschecks", new IndexCheckCollection());
            this.set("unoptimizable", new QualCollection());
            this.listenTo(this.get("datasource"), "metricgroup:dataload", this.update, this);
            this.listenTo(this.get("datasource"), "metricgroup:startload", this.startload, this);
            this.set("scoringMethod", ColumnScoringMethod);
        },

        startload: function(){
            this.trigger("wizard:start");
            this.trigger("widget:update_progress", "Fetching most executed quals...", 0);
        },

        launchOptimization: function(options){
            this.get("datasource").set("enabled", true);
            this.get("datasource").update(options.from_date, options.to_date);
            this.get("indexes").set([]);
            this.get("indexescheckserror").set([]);
            this.get("indexeschecks").set([]);
            this.get("unoptimizable").set([]);
        },

        /* Compute the links between quals.
         *
         * Two types of links are considered:
         *  - Almost-free links, where two predicates can be grouped together
         *  using a single index
         *  - Expensive links, where a new index has to be created.
         *
         * */
        computeLinks: function(nodes){
            var nodesToTrash = [];
            var nodes = nodes.models;
            for(var i=0; i <nodes.length; i++){
                var firstnode = nodes[i];
                this.trigger("widget:update_progress", "Building links  for node " + (i + 1) + " out of " + nodes.length,
                        (20 + ((i + 1) / nodes.length) * 10).toFixed(2));
                if(!firstnode.get("quals").some(function(qual){
                    return _.keys(qual.get("amops")).length > 0;
                })){
                    nodesToTrash.push(firstnode);
                    continue;
                }
                for(var j=0; j<i; j++){
                    var secondnode = nodes[j];
                    if(!secondnode.get("quals").some(function(qual){
                        return _.keys(qual.get("amops")).length > 0;
                    })){
                        nodesToTrash.push(secondnode);
                        continue;
                    }

                    nodesToTrash = _.uniq(nodesToTrash.concat(this.make_links(firstnode, secondnode)));
                }
            }
            _.each(nodes, function(nodesource){
                nodesource.get("contained").set( _.difference(nodesource.get("contained").models, nodesToTrash));
            });
            return [_.difference(nodes, nodesToTrash), nodesToTrash];
        },

        make_links: function (node1, node2) {
            // This functions assumes that qual1.quals and qual2.quals are sorted
            // according to the (relid,attnum,opno) tuple.
            // This is basically a merge-join.
            var idx1 = 0, idx2 = 0, l1 = node1.get("quals").models, l2 = node2.get("quals").models;
            var overlap = [];
            var attrs1 = {}, attrs2 = {};
            var relid1, relid2;
            var links = [];
            var missing1 = [], missing2 = [];
            l1 = new QualCollection(_.uniq(l1, false, function(q){ return [q.get("attnum"), q.get("relid")].join(".")})).models;
            l2 = new QualCollection(_.uniq(l2, false, function(q){ return [q.get("attnum"), q.get("relid")].join(".")})).models;
            if(node1.get("relid") != node2.get("relid")){
                return [];
            }
            while(true){
                if(idx1 >= l1.length || idx2 >= l2.length){
                    for(var i = idx1; i < l1.length; i++){
                        missing1.push(l1[i]);
                    }
                    for(var i = idx2; i < l2.length; i++){
                        missing2.push(l2[i]);
                    }
                    break;
                }
                var q1 = l1[idx1],
                    q2 = l2[idx2],
                    attrid1 = make_attrid(q1),
                    attrid2 = make_attrid(q2);
                if(attrs1[attrid1] === undefined){
                    attrs1[attrid1] = false;
                }
                if(attrs2[attrid2] === undefined){
                    attrs2[attrid2] = false;
                }
                relid2 = q2.get("relid");
                var isOverlap = false;
                if(q1.get("relid") == q2.get("relid") &&
                q1.get("attnum") == q2.get("attnum")){
                    var common_ams = _.filter(_.keys(q1.get("amops")), function(indexam){
                        return q2.get("amops")[indexam] != undefined;
                    });
                    if(common_ams.length > 0){
                        overlap.push({
                            relid: q1.get("relid"),
                            attnum: q1.get("attnum"),
                            relname: q1.get("relname"),
                            attname: q1.get("attname"),
                            indexams: common_ams,
                            q1_idx: idx1,
                            q2_idx: idx2
                        });
                        isOverlap = true;
                        attrs1[attrid1] = true;
                        attrs2[attrid2] = true;
                        idx1++;
                        idx2++;
                        continue;
                    }
                }
                if(!isOverlap){
                    if(node1.get("quals").comparator.call(q1, q1, q2) > 0){
                        missing2.push(q2);
                        idx2++;
                    } else {
                        missing1.push(q1);
                        idx1++;
                    }
                }
            }
            var samerel = relid1 != undefined && relid2 != undefined && relid1 == relid2;
            overlap = _.uniq(overlap, function(item){
                return item.attnum;
            });

            if(missing1.length == 0 && missing2.length == 0){
                node1.merge(node2);
                return [node2];
            }
            if(missing2.length == 0){
                node1.get("contained").add(node2);
            }
            if(missing1.length == 0){
                node2.get("contained").add(node1);
            }
            return [];
        },

        update: function(quals, from_date, to_date){
            var total_quals = _.size(quals);
            this.set("from_date", from_date);
            this.set("to_date", to_date);
            if (total_quals == 0){
                this.trigger("widget:update_progress", "No quals require optimization!", 100);
                this.trigger("wizard:end");
                return;
            } else {
                this.trigger("widget:update_progress", "Building nodes for " + total_quals + " quals ...", 0);
            }

            var nodes = new NodeCollection();
            _.each(quals, function(qual, index){
                var node = new QualModel({
                    label: qual.where_clause,
                    type: "qual",
                    quals: qual.quals,
                    from_date: from_date,
                    to_date: to_date,
                    queries: qual.queries,
                    queryids: qual.queryids,
                    relid: qual.relid,
                    relname: qual.relname,
                    nspname: qual.nspname,
                    links: {},
                    id: qual.qualid,
                });
                nodes.add(node);
                this.trigger("widget:update_progress", "Building nodes for " + total_quals + " quals ...",
                        10 + (10 * index / total_quals).toFixed(2));
            }, this);
            result = this.computeLinks(nodes);
            this.get("unoptimizable").set(result[1]);
            this.solve(result[0]);
            this.checkSolution();
            this.trigger("wizard:end");
        },

        checkSolution: function(){
            if(!this.get("has_hypopg")){
                this.trigger("widget:update_progress", "Install hypopg for solution validation",
                        100);
                return
            }

            if(this.get("indexes").size() == 0){
                this.trigger("widget:update_progress", "No indexes to suggest!",
                        100);
                return
            }
            this.trigger("widget:update_progress", "Checking solution with hypopg...",
                    60);
            var indexes = [], queryids = [];
            this.get("indexes").each(function(index){
                var node = _.clone(index.get("node").attributes);
                node['ams'] = index.get('ams');
                node['ddl'] = index.get('ddl');
                if(node['ams'].length > 0){
                    indexes.push(node);
                }
                queryids = _.uniq(queryids.concat(index.get("queryids")));
            });
            var self = this;
            $.ajax({
                url: '/server/' + this.get("server") +
                  '/database/' + this.get("database") + '/suggest/',
                data: JSON.stringify({
                    queryids: queryids,
                    indexes: indexes,
                    from_date: this.get("from_date"),
                    to_date: this.get("to_date")
                }),
                type: 'POST',
                contentType: 'application/json'
            }).success(function(data){
                _.each(data["inderrors"], function(err, ddl){
                    self.get("indexescheckserror").add({
                        _ddl: ddl,
                        _error: err
                    });
                });
                _.each(data["plans"], function(stat, id){
                    self.get("indexeschecks").add({
                        _query: stat.query,
                        _gain: stat.gain_percent
                    });
                });
                self.trigger("widget:update_progress", "Done !", 100);

            });
        },

        solve: function(nodes){
            var remainingNodes = nodes;
            var pathes = {};
            var makePathId = function(nodes){
                return _.map(nodes, function(node){ return node.get("id")}).join(",");
            };
            var self = this;
            var getPathes = function(node){
                var mypath = {
                    id: node.get("id"),
                    score: node.get("score"),
                    nodes: [node]
                };
                var pathes = [];
                node.get("contained").each(function(contained){
                    var child_pathes = getPathes(contained);
                    _.each(child_pathes, function(path){
                        var current_path = _.clone(path.nodes);
                        current_path.push(node);
                        pathes.push({
                            nodes: current_path,
                            id: makePathId(current_path),
                            score: self.get("scoringMethod").scorePath(nodes)
                        });
                    });
                }, this);
                pathes.push(mypath);
                return pathes;
            };

            // Compute score for each node.
            _.each(remainingNodes, function(node){
                node.set("score", this.get("scoringMethod").scoreNode(node));
            }, this);

            _.each(remainingNodes, function(node, idx){
                this.trigger("widget:update_progress", "Building pathes for node " + idx + " out of " +
                        nodes.length + " nodes ...",
                        30 + (10 * (idx / nodes.length).toFixed(2)));

                _.each(getPathes(node), function(path){
                    pathes[path.id] = path;
                });
            }, this);
            var safeguard = 0;
            var nbOptimized = 0;
            var nbPathes = _.keys(pathes).length;
            while(_.values(pathes).length > 0 && safeguard < 10000){
                safeguard++;
                /* Work with the remainging highest-scoring path */
                var firstPath = _.max(_.pairs(pathes), function(pair){
                    return pair[1].score;
                })[1];
                var root = firstPath.nodes.slice(-1)[0];
                /* Find attnum order */
                var attnums = [];
                var queryids = [];
                self.trigger("widget:update_progress", "Optimizing  " + nbOptimized + " out of " +
                        nbPathes + " pathes ...",
                        40 + (20 * (nbOptimized / nbPathes).toFixed(2)));



                _.each(firstPath.nodes, function(node, idx){
                    var nodeAttnum = node.get("quals").pluck("attnum");
                    var newAttnums = _.difference(nodeAttnum, attnums);
                    var idToDel = makePathId(firstPath.nodes.slice(0, idx+1));
                    attnums = attnums.concat(newAttnums);
                    _.each(_.pairs(pathes), function(pair){
                        var pathid = pair[0];
                        var path = pair[1];
                        if(path.nodes.indexOf(node) > -1){
                            var pathToDel = pathes[pathid];
                            nbOptimized++;
                            if(pathToDel){
                                self.trigger("widget:update_progress", "Optimizing  " + nbOptimized + " out of " +
                                        nbPathes + " pathes ...",
                                        40 + (20 * (nbOptimized / nbPathes).toFixed(2)));
                           }
                            delete pathes[pathid];
                        }
                    });
                    queryids = _.uniq(queryids.concat(node.get("queryids")));
                });
                var ams = _.flatten(firstPath.nodes.slice(-1)[0].get("quals").map(function(qual){
                    return _.keys(qual.get("amops"))
                }));
                ams = _.uniq(ams);
                this.get("indexes").add({
                    node: firstPath.nodes.slice(-1)[0],
                    path: firstPath.nodes,
                    attnums: attnums,
                    queryids: queryids,
                    ams: ams,
                    stub: true
                });
            }
        }

    }, {
        fromJSON: function(jsonobj){
            var group = DataSourceCollection.get_instance();
            jsonobj.datasource = group.findWhere({name: jsonobj.datasource});
            if(jsonobj.datasource === undefined){
                throw ("The content source could not be found.");
            }
            return new this(jsonobj);
        }
    });
});
