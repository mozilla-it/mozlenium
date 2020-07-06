# the wrapper edition!
echo 'var $result;' > $NODE_PATH/check.js
grep -v "require('mozlenium')();" $f >> $NODE_PATH/check.js
sed -i 's|^$browser|var $result = $browser|g' $NODE_PATH/check.js
echo -e 'module.exports = function() {\n  this.$result = $result;\n}' >> $NODE_PATH/check.js
f=wrapper.js

