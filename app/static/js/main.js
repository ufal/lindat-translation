$(document).ready(function() {

  // flash an alert
  function flash_alert(message, category) {
    //console.log(message);
    var out = $("#output_text");
    out.val(message);
    if(category === 'danger'){
        out.css("background-color", "#d9534f")
    }
  }

  function show_translation(translation) {
    $("#output_text").val(translation);
  }

  function create_option(value){
      var option = $("<option/>")
      option.attr('value', value)
      option.text(value)
      return option
  }

  function models_visible(){
      return !$("#models").parents("div.form-group").hasClass('hidden')
  }

  function get_action_url(){
      if (models_visible()){
          return $("#models option:selected").val()
      }else{
          return $("form").attr('action')
      }

  }

  function get_form_data(){
      var src_option = $("#source option:selected")
      var src = src_option.val()
      if(src_option.attr('name')){
          src = src_option.attr('name')
      }
      var i = src.lastIndexOf('/')
      if(i >= 0){
          src = src.substring(i + 1)
      }
      return {
          'input_text': $("#input_text").val(),
          'src': src,
          'tgt': $("#target option:selected").val()
      }
  }

  var progressFunction = function(message){
      var counter = 0;
      return setInterval(function() {
          var dots = Array((++counter % 5) + 2).join(".");
          var progressMessage = message + dots;
          flash_alert(progressMessage, "info");
      }, 1500)
  };

  // submit form
  $("#submit").on('click', function() {
    flash_alert("Running  ...", "info");
    var progress = progressFunction("Running ");
    $("#submit").attr("disabled", "disabled");
    $.ajax({
      url: get_action_url(),
      data: get_form_data(),
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

  var select_source = $("#source")
  var select_target = $("#target")
  // checkbox actions
  $("#advanced").change(function(){
      var models_parent = $("#models").parents("div.form-group").toggleClass('hidden')
      // models are visible, fetch the right src/tgt
      if (models_visible()){
          $("#models").trigger('change')
      }else{
          //init select_source
          $.ajax({
              url:$('form').attr("action"),
              dataType: "json",
              success: function(data, status, request){
                  select_source.find("option").remove()
                  data._embedded.item.forEach(function(lang_resource){
                     if (lang_resource._links.targets.length > 0){
                         var option = create_option(lang_resource.title)
                         option.val(lang_resource._links.self.href)
                         option.attr('name', lang_resource.name)
                         select_source.append(option)
                     }
                  })
              },
              error: function(jqXHR, textStatus, errorThrown){
                  console.error(textStatus)
              },

          }).done(function(){
              select_source.trigger('change')
          })
      }
  })

    var get_model_options = function(model_url){
      return $.ajax({
          url: model_url,
          dataType: "json",
          success: function(data, status, request){
              select_source.off('change.languages')
              select_source.find("option").remove()
              select_target.find("option").remove()
              Object.keys(data.supports).forEach(function(key){
                  var option = create_option(key)
                  select_source.append(option)
              })
              select_source.on('change.languages', function(e){
                  if (models_visible()) {
                      var key = $(e.target).val()
                      var supported_tgt_arr = data.supports[key]
                      select_target.find("option").remove()
                      supported_tgt_arr.forEach(function (tgt_lang) {
                          var option = create_option(tgt_lang)
                          select_target.append(option)
                      })
                  }
              })
              //add_options(select_target, data.target)
              //console.log(data)
          },
          error: function (jqXHR, textStatus, errorThrown) {
              console.error(textStatus)
          }
      })
    }
    $("#models").change(function(e){
        var model_url = $(e.target).val()
        get_model_options(model_url).done(function(){
            select_source.trigger('change')
        })
    })

    select_source.on('change.language.nomodel', function(e){
        if (!models_visible()){
            var selected_src_url = $(e.target).val()
            $.ajax({
              url: selected_src_url,
              dataType: "json",
              success: function(data, status, request){
                  var selected_target = $("#target option:selected").val()
                  select_target.find("option").remove()
                  data._links.targets.sort(function(a, b){
                      return a.title.localeCompare(b.title)
                  }).forEach(function(lang_link){
                      var option = create_option(lang_link.name)
                      if (lang_link.name == selected_target){
                          option.attr('selected', 'selected')
                      }
                      option.text(lang_link.title)
                      select_target.append(option)
                  })

              },
              error: function (jqXHR, textStatus, errorThrown) {
                console.error(textStatus)
              }
            })
        }
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

  // for switchboard
  let params = (new URL(document.location)).searchParams;
  let remoteFileURL = decodeURIComponent(params.get('remoteFileURL'));
  let requestedLang = params.get('requestedLang');
  let requestedLangOptionField = select_source.find("option[value$='"+requestedLang+"']");
  if(remoteFileURL && requestedLang && requestedLangOptionField.size() > 0 ){
      var progress = progressFunction("Getting " + remoteFileURL + " ");
      fetch(remoteFileURL,{
          headers: {
              'Accept': 'text/plain'
          }
      }).then((response) => {
          if(response.ok){
              const reader = response.body.getReader();
              // XXX 2 is a magical number
              let bytes_left_to_limit = $FILE_SIZE_LIMIT / 2;
              return new Response(new ReadableStream({
                  start(controller){
                      return pump();
                      function pump() {
                          return reader.read().then(({done, value}) => {
                              if(done || bytes_left_to_limit - value.length <= 0){
                                  if (value && bytes_left_to_limit - value.length <= 0) {
                                      value = value.slice(0, bytes_left_to_limit);
                                      controller.enqueue(value);
                                      reader.cancel();
                                      alert("The file is too large; truncating it.")
                                  }
                                  controller.close();
                                  return;
                              }
                              bytes_left_to_limit -= value.length;
                              controller.enqueue(value);
                              return pump();
                          })

                      }
                  }
              })
              ).text();
          }else{
              return Promise.reject(response.status + ":" + response.statusText);
          }
      }).then((text)=>{
          $("#input_text").val(text);
          select_source.val(requestedLangOptionField.val());
          select_source.trigger('change');
          cancelCountDown();
      }).catch((reason) => {
          flash_alert("Failed to fetch" + remoteFileURL + ":\n" + reason, "danger");
      }).finally(() => {
          clearInterval(progress);
      })
  }

  // textarea auto translate
    var countDownTimer;
    var cancelCountDown = function(){
        clearTimeout(countDownTimer)
        $("#submit").removeAttr("disabled");
        var out = $("#output_text");
        out.css("background-color", "");
        out.val("");
    }
    var countDown = function(){
        cancelCountDown()
        countDownTimer = setTimeout(function(){
            //console.log("sending " + $("#input_text").val())
            if($("#input_text").val()){
                $("#submit").click()
            }
        }, 1000)
    }
    // TODO mobile seems lacking keyup/keydown
    $("#input_text").on("keyup", countDown)
                    .on("keydown", cancelCountDown)
                    .on("paste", countDown)
    $("#models").on("change", countDown)
    $("#advanced").on("change", countDown)
    $("#source").on("change", countDown)
    $("#target").on("change", countDown)
});
