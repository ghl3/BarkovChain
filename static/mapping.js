
// To Do:

/*
  Consider creating a 'location' class that
  stores the following information:
  - Location Dictionary
  - Location Marker
  - Set of path LatLong (from previous location)
  - Marker color, additional info
  - Table entry as a javascript/jquery object

  And has methods to:
  - populat the path LatLon based on a previous destination
  - Create the marker from the dictionary
*/

// Global Variables
var map = null;
var marker = null;
var current_user_vector = null;
var venue_list = new Array();
var rejected_points = new Array();

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
    this.table_row.remove();
    // $("#venue_list").find('.row:last').remove();

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
    self.table_row = tail_row;

}


// The current chain, stored in 
// two arrays.  The first is a dictionary
// of locations, the second is the list
// of google maps markers
var active_chain = false;
var current_path = null;
var current_chain_locations = new Array();
var current_chain_markers = new Array();
var current_chain_latlon = new Array();
var rejected_points = new Array();


// Create a twitter bootstrap collapsable
// Object on-th-fly
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


function addDataToTable(data, columns) {

    /*    
    var table = $("#venue_table");

    var rowCount = $('#venue_table tr').length;
    // Create the header, if necessary
    if( rowCount==0 ) {
	var row = document.createElement("tr");
	for( var column_idx = 0; column_idx < columns.length; ++column_idx ) {
	    var cell = row.insertCell(column_idx);
	    cell.innerHTML = columns[column_idx];
	    cell.setAttribute("class", "table_header");
	}
	table.append(row);
    }
    var rowCount = $('#venue_table tr').length;
    */

    var table = $("#venue_list");
    var rowCount = $('#venue_list').find(".row").length;
    var tail_row = createTableRow(data, columns, rowCount );
    table.append(tail_row);
}


function createTableRow(data, columns, row_index) {

    console.log("Creating row Object " + row_index);

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
<div class="span4"> \
<div class="review"> </div> \
</div> \
<hr> \
</div>';

/*

<div class="span1"><a href="http://critterapp.pagodabox.com/others/admin" class="thumbnail"> \
<img src="http://critterapp.pagodabox.com/img/user.jpg" alt=""></a>\
</div> \


<span class="badge badge-info review" ></span> \

*/

    console.log("Row String:");
    console.log(row_html_string);
    
// Create the object
    var row = $(row_html_string);

    // Add the collapsable review
    var collapsable = createCollapsable("row_" + row_index, "review", data['review']);
    row.find(".review").html(collapsable);

    console.log("Created Row:");
    console.log(row);

    return row;

    /*
    // Recall that the header row is row=0
    var row = document.createElement("tr");

    for( var column_idx = 0; column_idx < columns.length; ++column_idx ) {
	var cell = row.insertCell(column_idx);
	var var_name = columns[column_idx];
	if(var_name != 'review') {
	    cell.innerHTML = data[var_name];
	}
	else {
	    var collapsable = createCollapsable("row_" + row_index, 
						"review", data[var_name]); 
	    cell.innerHTML = collapsable;
	}
	cell.className += "table_column_" + column_idx;
    }
    
    return row;
*/
}


function beginChain(event) {

    // First, check if there is an existing
    // chain.  If so, we kill it.
    if(active_chain==true) {
	clearChain();
    }

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

    /////////////////////////////////////////////////////////
    /////////////////////////////////////////////////////////
    /////////////////////////////////////////////////////////


    current_chain_latlon.push(new Array(latlon));
    
    // Create the 'begin' marker
    marker = new google.maps.Marker({
	position: latlon,
	map: map,
	animation: google.maps.Animation.DROP,
	name : "Starting Point"
    });
    current_chain_markers.push(marker);

    // Create a 'location'
    var location = {}; //new Array();
    location['latitude'] = latlon.lat();
    location['longitude'] = latlon.lng();
    location['initial'] = true;
    current_chain_locations.push(location);
    console.log("Starting Point:");
    console.log(location);

    active_chain = true;

}


// Update the shown path based on the current
// List of LatLon points
function updatePath() {
    
    console.log("updating Path");

    // Create the path, including directions
    // if necessary
    if( current_path == null ) {
	current_path = new google.maps.Polyline({
	    strokeColor: "#0000FF",
	    strokeOpacity: 0.8,
	    strokeWeight: 4
	});
        current_path.setMap(map);
    }

    console.log("Appending to path");

    var total_chain = new Array();
    for(var i=0; i < venue_list.length; ++i) {
	console.log("venue list: " + i);
	console.log(venue_list[i]);
	var path = venue_list[i].path;
	if( path == null ) continue;
	console.log("Appending path");
	console.log(path);
	total_chain = total_chain.concat(path);
    }
    console.log("Setting current path");
    console.log(total_chain);
    current_path.setPath(total_chain);
}


function addToChain(location_dict) {

    console.log("Adding new location:");
    console.log(location_dict);

    // Create a new venue
    var next_venue = new venue(location_dict);
    venue_list.push(next_venue);

    // Get the updated path between the last point
    // and the new point
    var last_lat_long = venue_list[venue_list.length - 1].latlon;
    var next_lat_long = next_venue.latlon;

    var service = new google.maps.DirectionsService();
    service.route({
	origin: last_lat_long,
	destination: next_lat_long,
	travelMode: google.maps.DirectionsTravelMode.WALKING
    }, function(result, status) {
	if (status == google.maps.DirectionsStatus.OK) {
	    console.log("Successfully found gMaps path");
	    var new_path = result.routes[0].overview_path;
	    next_venue.path = new_path;
	    updatePath();
	}
	else {
	    console.log("Travel Directions Error");
	}
    });

    // Need to add the table
    next_venue.add_to_table();

    return;

    /////////////////////////////////////////////////
    /////////////////////////////////////////////////
    /////////////////////////////////////////////////


    current_chain_locations.push(location_dict);

    var lat = location_dict['latitude'];
    var lon = location_dict['longitude'];
    var latlon = new google.maps.LatLng(lat, lon);

    var marker = new google.maps.Marker({
	position: latlon,
	map: map,
	animation: google.maps.Animation.DROP
    });
    current_chain_markers.push(marker);

    // Create the path, including directions
    if( current_path == null ) {
	current_path = new google.maps.Polyline({
	    strokeColor: "#0000FF",
	    strokeOpacity: 0.8,
	    strokeWeight: 4
	});
        current_path.setMap(map);
    }

    // Get the origin
    // Recall, current_chain_latlon is a list of lists
    var last_chain_group = current_chain_latlon[current_chain_latlon.length-1];
    var last_point = last_chain_group[last_chain_group.length-1];

    var service = new google.maps.DirectionsService();
    service.route({
	origin: last_point,
	destination: latlon,
	travelMode: google.maps.DirectionsTravelMode.WALKING
    }, function(result, status) {
	if (status == google.maps.DirectionsStatus.OK) {
	    var new_path = result.routes[0].overview_path;
	    current_chain_latlon.push(new_path);	    
	    updatePath();
	}
	else {
	    console.log("Travel Directions Error");
	}
    });

    // Append to the table
    addDataToTable(location_dict, ["name", "address", "review"]);

}


function clearChain() {

    // Clear the array
    for(var i=0; i < venue_list.length; ++i) {
	venue_list[i].clear();
    }
    venue_list.length = 0;
    active_chain = false;
    return;

    //////////////////////////////////////////////////
    //////////////////////////////////////////////////
    //////////////////////////////////////////////////


    // Clear the arrays
    for(var i=0; i<current_chain_markers.length; ++i) {
	current_chain_markers[i].setMap(null);
    }

    current_chain_markers.length = 0;
    current_chain_locations.length = 0;
    current_chain_latlon.length = 0;

    // Clear the path
    if( current_path != null ) current_path.setMap(null);
    current_path = null;

    // Clear the table
    $('#venue_table').empty();

    active_chain = false;
    $("#venue_list").hide();
}


// Get the next 'location' based on the current
// chain of locations
function getNextLocation(accepted) {

    if(active_chain == false) {
	console.log("Cannot submit to server, chain isn't yet active");
	return;
    }

    if( venue_list.length == 0 ) {
	console.log("Error: No locations exist yet");
	return;
    }

    if( venue_list.length == 1 ){
	var data = {'location' : venue_list[0].data}
	submitToServer('/api/initial_location', data);
    }
    
    else {

	// Create the chain of locations
	var chain = new Array();
	for( var i = 0; i < venue_list.length; ++i) {
	    chain.push(venue_list[i].data);
	}

	var data = {'chain' : chain,
		    'rejected_points' : rejected_points,
		    'user_vector' : current_user_vector,
		    'accepted' : accepted};
	submitToServer('/api/next_location', data);
    }

    return;

	////////////////////////////////////////////////
	////////////////////////////////////////////////
	////////////////////////////////////////////////

    if( current_chain_locations.length == 0 ) {
	console.log("Error: No locations exist yet");
	return;
    }

    if( current_chain_locations.length == 1 ){
	var data = {'location' : current_chain_locations[0]}
	submitToServer('/api/initial_location', data);
    }
    
    else {
	var data = {'chain' : current_chain_locations,
		    'rejected_points' : rejected_points,
		    'user_vector' : current_user_vector,
		    'accepted' : accepted};
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
function rejectLastPoint() {

    // Delete the last set of points in the array
    var last_marker = current_chain_markers.pop();
    last_marker.setMap(null);

    // WARNING: 
    // IF THE USER REJECTS THE LAST POINT, WE WANT TO
    // BLACKLIST IT SOMEHOW.  WE'LL NEED TO MAINTAIN
    // SUCH A LIST
    var last_location = current_chain_locations.pop();
    rejected_points.push(last_location);

    current_chain_latlon.pop();
    updatePath();

    $("#venue_list").find('.row:last').remove();

    var rowCount = $('#venue_list').find(".row").length;
    if(rowCount==0) {
	clearChain();
    }

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
    // map = new google.maps.Map(document.getElementById("map_canvas"), mapOptions);
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
