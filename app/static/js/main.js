$(document).ready(function() {
   var visible_select_box_id = '#lang_pair'

  // flash an alert
  // remove previous alerts by default
  // set clean to false to keep old alerts
  function flash_alert(message, category, clean) {
    console.log(message);
    if (typeof(clean) === "undefined") clean = true;
    if(clean) {
      remove_alerts();
    }
    var htmlString = '<div class="alert alert-' + category + ' alert-dismissible" role="alert">'
    htmlString += '<button type="button" class="close" data-dismiss="alert" aria-label="Close">'
    htmlString += '<span aria-hidden="true">&times;</span></button>' + message + '</div>'
    $(htmlString).prependTo(".panel-group").hide().slideDown();
  }

  function remove_alerts() {
    $(".alert").slideUp("normal", function() {
      $(this).remove();
    });
  }

  function show_translation(translation) {
    $("#output_text").val(translation);
  }

  // submit form
  $("#submit").on('click', function() {
    flash_alert("Running  ...", "info");
    var counter = 0;
    var progress = setInterval(function() {
          var dots = Array((++counter % 5) + 2).join(".");
          var message = "Running" + dots;
          flash_alert(message, "info");
      }, 1500);
    $("#submit").attr("disabled", "disabled");
    $.ajax({
      url: $(visible_select_box_id + " option:selected").val(),
      data: {'input_text': $("#input_text").val()},
      method: "POST",
      dataType: "json",
      success: function(data, status, request) {
          clearInterval(progress);
          flash_alert("Success", "success");
          show_translation(data.join(' ').replace(/\n /g, '\n'));
          $("#submit").removeAttr("disabled");
      },
      error: function(jqXHR, textStatus, errorThrown) {
          clearInterval(progress);
          flash_alert("Translation failed: " + textStatus + "\n" + errorThrown, "danger");
      }
    });
  });

  // checkbox actions
  $("#advanced").change(function(){
      $("#models").parents("div.form-group").toggleClass('hidden')
      $("#lang_pair").parents("div.form-group").toggleClass('hidden')
      visible_select_box_id = '#' + $("div.form-group:not(.hidden) > select").attr('id')
  })

  // fileupload
  if (!!FileReader && 'draggable' in document.createElement('span')
			&& !!window.FormData && "upload" in new XMLHttpRequest && !!window.Blob && !!window.FileReader) {
            var $file_field = $("input[type='file']")
				$file_field.change(function() {
                    var files = document.getElementById("data_file").files;
                    if(files.length > 0) {
                        if (files[0].size > $FILE_SIZE_LIMIT) {
                            alert('The file is too large.\nThe maximal allowed content length is ' + $FILE_SIZE_LIMIT + 'B.')
                            event.preventDefault()
                            return
                        }
                        if (files[0].type !== 'text/plain'){
                            alert(files[0].type + ' not allowed. Only text/plain.')
                            event.preventDefault()
                            return
                        }
                        var reader = new FileReader();
                        reader.onload = function(event){
                            $("#input_text").val(event.target.result)
                            $("#input_text").trigger('paste')
                        }
                        //console.log(files[0])
                        reader.readAsText(files[0]);
                    }
				});
		}

  // textarea auto translate
    var countDownTimer;
    var cancelCountDown = function(){
        clearTimeout(countDownTimer)
    }
    var countDown = function(){
        cancelCountDown()
        countDownTimer = setTimeout(function(){
            //console.log("sending " + $("#input_text").val())
            if($("#input_text").val()){
                $("#submit").click()
            }
        }, 1500)
    }
    $("#input_text").on("keyup", countDown)
                    .on("keydown", cancelCountDown)
                    .on("paste", countDown)
    $("#lang_pair").on("change", countDown)
    $("#models").on("change", countDown)
    $("#advanced").on("change", countDown)
});
