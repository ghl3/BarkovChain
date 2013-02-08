
function test() {

    this.fish = "fish";
    console.log("Testing");
    this.plot = null;

}


function bubble_plot(id, width, height) {
    
    this.id = id;
    this.width = width;
    this.height = height;

}


bubble_plot.prototype.make_chart = function() {

    var self = this;

    var chart, clear, click, collide, collisionPadding, connectEvents, data, gravity,  idValue, jitter, label, maxRadius, minCollisionRadius, mouseout, mouseover, node, rScale, rValue, textValue, tick, transformData, update, updateActive, updateLabels, updateNodes;

    //	width = 980;
    //	height = 510;
    this.data = [];
    var data = this.data;

    node = null;
    label = null;
    this.margin = {
	top: 5,
	right: 0,
	bottom: 0,
	left: 0
    };

    var margin = this.margin;

    maxRadius = 65;
    this.rScale = d3.scale.sqrt().range([0, maxRadius]);
    this.rValue = function(d) {
	return parseInt(d.count);
    };

    var rValue = this.rValue;
    var rScale = this.rScale;

    idValue = function(d) {
	return d.name;
    };

    textValue = function(d) {
	return d.name;
    };

    collisionPadding = 4;
    minCollisionRadius = 12;
    jitter = 0.5;

    this.transformData = function(rawData) {
	rawData.forEach(function(d) {
	    d.count = parseInt(d.count);
	    return rawData.sort(function() {
		return 0.5 - Math.random();
	    });
	});
	return rawData;
    };
    var transformData = this.transformData;

    tick = function(e) {

	var dampenedAlpha;

	dampenedAlpha = e.alpha * 0.1;

	node.each(gravity(dampenedAlpha)).each(collide(jitter)).attr("transform", function(d) {
	    return "translate(" + d.x + "," + d.y + ")";
	});
	
	return label.style("left", function(d) {
	    return ((margin.left + d.x) - d.dx / 2) + "px";
	}).style("top", function(d) {
	    return ((margin.top + d.y) - d.dy / 2) + "px";
	});
	
    };

    this.force = d3.layout.force().gravity(0).charge(0).size([self.width, self.height])
	.on("tick", tick);

    var force = this.force;


    add_data = function(rawData) {

	var maxDomainValue, svg, svgEnter;

	data = transformData(rawData);

	maxDomainValue = d3.max(data, function(d) {
	    return rValue(d);
	});

	rScale.domain([0, maxDomainValue]);
	svg = d3.select(this).selectAll("svg").data([data]);
	
	svgEnter = svg.enter().append("svg");
	
	svg.attr("width", self.width + margin.left + margin.right);
	svg.attr("height", self.height + margin.top + margin.bottom);
	
	node = svgEnter.append("g").attr("id", "bubble-nodes")
	    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
	
	node.append("rect").attr("id", "bubble-background").attr("width", self.width)
	    .attr("height", self.height);
	
	label = d3.select(this).selectAll("#bubble-labels").data([data])
	    .enter().append("div").attr("id", "bubble-labels");
	
	update();
	return;
    }
    
    // Create the chart
    chart = function(selection) {
	return selection.each(add_data);
    };

    this.update = function() {
	data.forEach(function(d, i) {
	    return d.forceR = Math.max(minCollisionRadius, rScale(rValue(d)));
	});
	force.nodes(data).start();
	updateNodes();
	return updateLabels();
    };
    var update = this.update;

    updateNodes = function() {
	node = node.selectAll(".bubble-node").data(data, function(d) {
	    return idValue(d);
	});
	node.exit().remove();
	return node.enter().append("a").attr("class", "bubble-node")
	    .call(force.drag).call(connectEvents).append("circle").attr("r", function(d) {
		return rScale(rValue(d));
	    });
    };

    updateLabels = function() {

	var labelEnter;

	label = label.selectAll(".bubble-label").data(data, function(d) {
	    return idValue(d);
	});

	label.exit().remove();

	labelEnter = label.enter().append("a").attr("class", "bubble-label")
	    .call(force.drag).call(connectEvents);
	labelEnter.append("div").attr("class", "bubble-label-name").text(function(d) {
	    return textValue(d);
	});

	labelEnter.append("div").attr("class", "bubble-label-value").text(function(d) {
	    return rValue(d);
	});

	label.style("font-size", function(d) {
	    return Math.max(8, rScale(rValue(d) / 2)) + "px";
	}).style("width", function(d) {
	    return 2.5 * rScale(rValue(d)) + "px";
	});

	label.append("span").text(function(d) {
	    return textValue(d);
	}).each(function(d) {
	    return d.dx = Math.max(2.5 * rScale(rValue(d)), this.getBoundingClientRect().width);
	}).remove();

	label.style("width", function(d) {
	    return d.dx + "px";
	});

	return label.each(function(d) {
	    return d.dy = this.getBoundingClientRect().height;
	});
    };

    this.gravity = function(alpha) {
	var ax, ay, cx, cy;
	cx = self.width / 2;
	cy = self.height / 2;
	ax = alpha / 8;
	ay = alpha;
	return function(d) {
	    d.x += (cx - d.x) * ax;
	    return d.y += (cy - d.y) * ay;
	};
    };

    var gravity = this.gravity;

    this.collide = function(jitter) {
	return function(d) {
	    return data.forEach(function(d2) {
		var distance, minDistance, moveX, moveY, x, y;
		if (d !== d2) {
		    x = d.x - d2.x;
		    y = d.y - d2.y;
		    distance = Math.sqrt(x * x + y * y);
		    minDistance = d.forceR + d2.forceR + collisionPadding;
		    if (distance < minDistance) {
			distance = (distance - minDistance) / distance * jitter;
			moveX = x * distance;
			moveY = y * distance;
			d.x -= moveX;
			d.y -= moveY;
			d2.x += moveX;
			return d2.y += moveY;
		    }
		}
	    });
	};
    };

    var collide = this.collide;

    this.connectEvents = function(d) {
	d.on("click", click);
	d.on("mouseover", mouseover);
	return d.on("mouseout", mouseout);
    };

    var connectEvents = this.connectEvents;

    click = function(d) {
	console.log(idValue(d));
	return d3.event.preventDefault();
    };

    updateActive = function(id) {
	node.classed("bubble-selected", function(d) {
	    return id === idValue(d);
	});
    };

    mouseover = function(d) {
	return node.classed("bubble-hover", function(p) {
	    return p === d;
	});
    };

    mouseout = function(d) {
	return node.classed("bubble-hover", false);
    };

    chart.jitter = function(_) {
	if (!arguments.length) {
	    return jitter;
	}
	jitter = _;
	force.start();
	return chart;
    };

    chart.height = function(_) {
	if (!arguments.length) {
	    return self.height;
	}
	self.height = _;
	return chart;
    };

    chart.width = function(_) {
	if (!arguments.length) {
	    return self.width;
	}
	self.width = _;
	return chart;
    };

    chart.r = function(_) {
	if (!arguments.length) {
	    return rValue;
	}
	rValue = _;
	return chart;
    };

    return chart;

};

/*
  $(function() {

  var display, key, text;
  //plot = Bubbles();
  display = function(data) {
  return plotData(id, data, plot);
  };

  d3.select("#jitter").on("input", function() {
  return plot.jitter(parseFloat(this.output.value));
  });

  display(word_data);
  return;
  });
*/


bubble_plot.prototype.plotData = function(selector, data, plot) {
    return d3.select(selector).datum(data).call(plot);
};

bubble_plot.prototype.draw = function(word_data) {

    console.log("Drawing Data:");
    console.log(word_data);
    
    // Create the plotting function
    this.plot = this.make_chart();

    d3.select("#jitter").on("input", function() {
	return this.plot.jitter(parseFloat(this.output.value));
    });

    return d3.select(this.id).datum(word_data).call(this.plot);

//    return this.plotData(this.id, word_data, this.plot);


/*
    if(this.plot == null) {
	this.plot = this.make_chart();
    }

    d3.select("#jitter").on("input", function() {
	return this.plot.jitter(parseFloat(this.output.value));
    });

    return this.plotData(this.id, word_data, this.plot);
*/

    /*
    display = function(data) {
	return self.plotData(self.id, data, self.plot);
    };
    return display(word_data);
    */
};


bubble_plot.prototype.update = function(word_data) {

    var self = this;

    console.log("updating bubbles");
    console.log(word_data);

    //var dampenedAlpha = 1.0;
    var     jitter = 0.5;

    d3.select(this.id).select("svg").select("#bubble-nodes")
	.selectAll(".bubble_node").data(word_data).enter()
	.append("a").attr("class", "bubble-node")
	.call(this.force.drag).call(this.connectEvents).append("circle").attr("r", function(d) {
	    return self.rScale(self.rValue(d));
	});
    
    d3.select(this.id).select("svg").select("#bubble-labels")
	.selectAll(".bubble-label").data(word_data).enter()
	.append("div").attr("id", "bubble-labels");
    
    this.data = this.data + this.transformData(word_data);
    this.update();
    
/*
	.each(self.gravity(dampenedAlpha)).each(self.collide(jitter))
	    .attr("transform", function(d) {
	    return "translate(" + d.x + "," + d.y + ")";
	})
*/
    
    // svgEnter = svg.enter();
    
    //svg.attr("width", self.width + this.margin.left + this.margin.right);
    // svg.attr("height", self.height + this.margin.top + this.margin.bottom);
    
    //node = svgEnter.append("g").attr("id", "bubble-nodes")
    //	.attr("transform", "translate(" + this.margin.left + "," + this.margin.top + ")");
    
    //node.append("rect").attr("id", "bubble-background").attr("width", self.width)
//	.attr("height", self.height);
    
}

