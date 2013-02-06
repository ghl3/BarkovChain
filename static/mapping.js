
// Global Variables
var map = null;
var marker = null;
var current_user_vector = null;
var venue_list = new Array();
var rejected_locations = new Array();
var current_path = null;
var active_chain = false;

// Venue class
function venue(data) {

    var self = this;
    this.data = data;

    // Create the lat/lon object
    var lat = data['latitude'];
    var lon = data['longitude'];
    this.latlon = new google.maps.LatLng(lat, lon);

    // Create the marker
    var marker = new google.maps.Marker({
	position: self.latlon,
	map: map,
	animation: google.maps.Animation.DROP
    });
    this.marker = marker;
    
    // To be filled later
    this.path = new Array(self.latlon);
    this.table_row = null;

}

venue.prototype.clear = function() {

    // Remove the marker from the map
    this.marker.setMap(null);

    // Remove the entry from the table    
    if( this.table_row != null ) {
	console.log("Removing table entry");
	this.table_row.remove();
    }
}

venue.prototype.add_path = function(last_point) {
    var self = this;
    var service = new google.maps.DirectionsService();
    service.route({
	origin: last_point,
	destination: latlon,
	travelMode: google.maps.DirectionsTravelMode.WALKING
    }, function(result, status) {
	if (status == google.maps.DirectionsStatus.OK) {
	    var new_path = result.routes[0].overview_path;
	    self.path = new_path;
	    return new_path;
	}
	else {
	    console.log("Travel Directions Error");
	}
    });
}

venue.prototype.add_to_table = function() {
    var table = $("#venue_list");
    var rowCount = $('#venue_list').find(".row").length;
    var columns = ["name", "address", "review"];
    var tail_row = createTableRow(this.data, columns, rowCount );
    table.append(tail_row);
    this.table_row = tail_row;
}


venue.prototype.create_path = function(last_lat_long, callback) {

    var self = this;

    var service = new google.maps.DirectionsService();
    service.route({
	origin: last_lat_long,
	destination: self.latlon,
	travelMode: google.maps.DirectionsTravelMode.WALKING
    }, function(result, status) {
	if (status == google.maps.DirectionsStatus.OK) {
	    var new_path = result.routes[0].overview_path;
	    self.path = new_path;
	    callback();
	}
	else {
	    console.log("Travel Directions Error");
	}
    });
}


// Create a twitter bootstrap collapsable
// It consists of two parts:
//   - The button that toggles the collapse
//   - The data section
// The 'id' input is the idea of the entire block
// The 'title' is the name on the toggle button
// The 'content' is the data that gets shown and hidden
// This function returns an html string
function createCollapsable(id, title, content) {

    var html_string = ' \
	<div class="accordion" id="' + id + '"> \
	 <div class="accordion-group"> \
          <div class="accordion-heading"> \
	    <a class="accordion-toggle" data-toggle="collapse" \
               data-parent="#' + id + '" href="#collapse_' + id + '"> \
	      ' + title + ' \
	    </a> \
	  </div> \
	  <div id="collapse_' + id + '" class="accordion-body collapse"> \
	    <div class="accordion-inner"> \
	      ' + content + ' \
	    </div> \
	  </div> \
	</div> \
      </div>';

    return html_string;

}


function createTableRow(data, columns, row_index) {

    console.log("Creating row Object " + row_index);

    console.log(data);

    var name = data['name'];
    var address = data['address'];

    var category_string = '';
    var category_list = data['categories'];
    for(var i=0; i < category_list.length; ++i) {
	category_string += category_list[i];
	if(i != category_list.length-1) {
	    category_string += ", ";   
	}
    }

    var row_html_string = ' \
<div class="row" id="row_' + row_index + '"> \
<div class="span3"> \
<p><strong>' + name + '</strong></p> \
<p>' + address + '</p> \
</div> \
<div class="span3">' + category_string + '</div> \
<div class="span2"> \
<div class="review"> </div> \
</div> \
<div class="span2"> \
<div class="tips"> </div> \
</div> \
<hr> \
</div>';
    
    // Create the object
    var row = $(row_html_string);

    // Add the collapsable review
    var collapsable = createCollapsable("row_" + row_index + "_review", "review", data['review']);
    row.find(".review").html(collapsable);

    // Add the collapsable tips
    var collapsable = createCollapsable("row_" + row_index + "_tips", "tips", data['review']);
    row.find(".tips").html(collapsable);

    return row;
}


function beginChain(event) {

    // First, check if there is an existing
    // chain.  If so, we kill it.
    if(active_chain==true) {
	clearChain();
    }

    // Create a new path
    current_path = new google.maps.Polyline({
	strokeColor: "#0000FF",
	strokeOpacity: 0.8,
	strokeWeight: 4
    });
    current_path.setMap(map);

    // To be done by clicking
    latlon = event.latLng;
    var data = {};
    data['latitude'] = latlon.lat();
    data['longitude'] = latlon.lng();
    data['initial'] = true;

    // Create the new object
    var initial_location = new venue(data);
    venue_list.push(initial_location);
    active_chain = true;
    return;

}


// Update the shown path based on the current
// List of LatLon points
function updatePath() {
    var total_chain = new Array();
    for(var i=0; i < venue_list.length; ++i) {
	var path = venue_list[i].path;
	total_chain = total_chain.concat(path);
    }
    current_path.setPath(total_chain);
}


function addToChain(location_dict) {

    console.log("Adding new location:");
    console.log(location_dict);

    // Create a new venue
    var next_venue = new venue(location_dict);
    venue_list.push(next_venue);

    // Add to the table
    next_venue.add_to_table();

    // Get the updated path between the last point
    // and the new point
    var last_lat_long = venue_list[venue_list.length - 1].latlon;
    next_venue.create_path(last_lat_long, updatePath);

    return;
}


function clearChain() {

    // Clear the array
    for(var i=0; i < venue_list.length; ++i) {
	venue_list[i].clear();
    }
    venue_list.length = 0;

    current_path.setMap(null);
    current_path = null;

    $("#venue_list").hide();
    active_chain = false;
    return;

}


// Get the next 'location' based on the current
// chain of locations
function getNextLocation(accepted) {

    if(active_chain == false) {
	console.log("Cannot submit to server, chain isn't yet active");
	return;
    }

    if( venue_list.length == 0 ) {
	console.log("Error: No venues exist yet");
	return;
    }

    // If we only have the inital marker, we
    // must use a special api point
    if( venue_list.length == 1 ){
	var data = {'location' : venue_list[0].data}
	submitToServer('/api/initial_location', data);
    }
    
    // Otherwise, we get the next venue basee
    // on the current chain
    else {
	var chain = new Array();
	for( var i = 0; i < venue_list.length; ++i) {
	    chain.push(venue_list[i].data);
	}

	var data = {'chain' : chain,
		    'rejected_locations' : rejected_locations,
		    'user_vector' : current_user_vector,
		    'accepted' : accepted};
	if( accepted ) data['last_venue'] = chain[chain.length-1]; 
	else data['last_venue'] = rejected_locations[rejected_locations.length-1];
	submitToServer('/api/next_location', data);
    }

}

// Wrapper for the server POST request.
// The returned JSON defines the next location
// and the updated user_vector
function submitToServer(api, data) {

    console.log('Submitting Location To Server: ' + api);
    console.log("Sending data:");
    console.log(data);

    function successfulCallback(data) {
	console.log("Server successfully returned data:");
	console.log(data);

	// Add the new location to the chain
	addToChain(data['location']);

	// Update the current user vector
	current_user_vector = data['user_vector'];
	console.log("Updated user vector:");
	console.log(current_user_vector);
	
	$("#venue_list").show();
    }
    
    function errorCallback(data) {
	console.log("Server encountered an error");
	console.log(data);
    }

    $.ajax({
	url: api,
	type: "POST",
	dataType: 'json',
	contentType:"application/json; charset=utf-8",
	mimeType : "string",
	data: JSON.stringify(data)
    })
	.done(successfulCallback)
	.fail(errorCallback)
	.always(function() { 
	    console.log("Server transaction complete");
	});
    
    console.log("Sent 'next_location' request to server. Waiting...");    

}


// Remove the last restaurant from
// the current chain
// Add the last marker to the list of 
function rejectLastPoint() {
    var last_venue = venue_list.pop();
    last_venue.clear();
    rejected_locations.push(last_venue.data);
}


// Create the google maps MAP
function create_map() {
    var mapOptions = {
	center: new google.maps.LatLng(40.77482, -73.96872),
	zoom: 13,
	mapTypeId: google.maps.MapTypeId.ROADMAP,
	//draggable: false,
	//scrollwheel: false,
	minZoom: 13, maxZoom: 18
    };
    return new google.maps.Map(document.getElementById("map_canvas"), mapOptions);
}


// Load the page! 
$(document).ready(function() {

    $("#venue_list").hide();
    
    // Create the map
    map = create_map();

    // Define clicking on the map
    google.maps.event.addListener(map, 'click', beginChain); 

    // Define clicking on the 'submit' button
    // Send an ajax request to the flask server
    // and get some info
    $("#button_accept").click(function() {
	getNextLocation(true);
    });

    $("#button_try_another").click(function() {
	rejectLastPoint();
	getNextLocation(false);
    });

});
