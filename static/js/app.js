
window.onload = function () {
  var re1 = /\/admin\/plpPool\/questao\/[0-9]*\/change/i;
  var re2 = /\/admin\/plpPool\/questao\/add/i;
  var re3 = /monitor/i;
  if (window.location.href.match(re1) || window.location.href.match(re2)) {
    document.getElementById('id_tags_to').setAttribute('style', '');
  }

  if (window.location.href.match(re1) || window.location.href.match(re2) || window.location.href.match(re3)) {
    var textareas = Array.from(document.getElementsByTagName('textarea'))
    textareas.forEach(function (textarea) {
      textarea.addEventListener('keydown', function(e) {
        if (e.key == 'Tab') {
          e.preventDefault();
          var start = this.selectionStart;
          var end = this.selectionEnd;
      
          this.value = this.value.substring(0, start) + "\t" + this.value.substring(end);
          this.selectionStart = this.selectionEnd = start + 1;
        }
      })
    })
  }

  var re1 = /monitor/i;
  var re2 = /admin/i;
  if (window.location.href.match(re1) && !window.location.href.match(re2)) {
    let testForm = document.querySelectorAll(".test-form")
    let container = document.querySelector("#form-container")
    let addButton = document.querySelector("#add-form")
    let bntsForm = document.querySelector("#bnt-test-form")
    let totalForms = document.querySelector("#id_form-TOTAL_FORMS")

    let formNum = testForm.length-1
    addButton.addEventListener('click', addForm)

    function addForm(e){
      e.preventDefault()
      
      let newForm = testForm[0].cloneNode(true)
      let formRegex = RegExp(`form-(\\d){1}-`,'g')
      
      formNum++
      newForm.innerHTML = newForm.innerHTML.replace(formRegex, `form-${formNum}-`)
      container.insertBefore(newForm, bntsForm)
      
      totalForms.setAttribute('value', `${formNum+1}`)
    }
  }

  var re = /admin/i;
  if (!window.location.href.match(re)) {
    $(function() { 
      $('#chkveg1').multiselect({ 
        includeSelectAllOption: true,     
        nSelectedText: 'selecionadas',
        nonSelectedText: 'Tags', 
        selectAllText: 'Todas',
        allSelectedText: 'Todas tags selecionadas',
        maxHeight: 150,
        buttonWidth: 250,
      }); 
      $('#chkveg2').multiselect({ 
        includeSelectAllOption: true,     
        nSelectedText: 'selecionados',
        nonSelectedText: 'Períodos', 
        selectAllText: 'Todos',
        allSelectedText: 'Todos períodos selecionados',
        maxHeight: 150,
        buttonWidth: 250,
      }); 
      $('#chkveg3').multiselect({ 
        includeSelectAllOption: true,     
        nSelectedText: 'selecionadas',
        nonSelectedText: 'Linguagens', 
        selectAllText: 'Todas',
        allSelectedText: 'Todas linguagens selecionadas',
        maxHeight: 150,
        buttonWidth: 250,
      }); 
    });
  }

  var textareas = document.getElementsByTagName('textarea');
  for (var i = 0; i < textareas.length; i++) {
    textareas[i].setAttribute('spellcheck', 'false');
  }

};


function changePage(page) {
  let visualizar = document.getElementById("visualizar");
  let modificar = document.getElementById("modificar");

  let preview = document.getElementById("preview");
  let form = document.getElementById("content-main");

  if (page == 'visualizar') {
    if (!visualizar.className.includes('selected')) {
      modificar.setAttribute('class', '');
      visualizar.setAttribute('class', 'selected');
      visualizar.setAttribute('style', 'text-decoration: underline; font-weight: bold;');
      modificar.setAttribute('style', '');

      preview.setAttribute('style', 'display: block;');
      form.setAttribute('style', 'display: none;');
    }
  } else if (page == 'modificar') {
    if (!modificar.className.includes('selected')) {
      modificar.setAttribute('class', 'selected');
      visualizar.setAttribute('class', '');
      modificar.setAttribute('style', 'text-decoration: underline; font-weight: bold;');
      visualizar.setAttribute('style', '');

      preview.setAttribute('style', 'display: none;');
      form.setAttribute('style', 'display: block;');
    }
  }
}

function showMenu() {
  let bnt = document.getElementById("bnt-menu-lateral");
  let menu = document.getElementById("menu-content");

  if (menu.getAttribute('style') == 'display: none;') {
    bnt.innerHTML = '<i class="fa-solid fa-arrow-up"></i>';
    menu.setAttribute('style', 'display: block;');
  } else {
    bnt.innerHTML = '<i class="fa-solid fa-arrow-down"></i>';
    menu.setAttribute('style', 'display: none;');
  }
}

function clipboard(element_id) {
  var copyText = document.getElementById(element_id);
  navigator.clipboard.writeText(copyText.value);
}
