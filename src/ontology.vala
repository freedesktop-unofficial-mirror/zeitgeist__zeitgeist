/* datamodel.vala
 *
 * Copyright © 2011 Collabora Ltd.
 *             By Seif Lotfy <seif@lotfy.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 2.1 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */
 

public class Symbol
{
    private static HashTable<string, Symbol> all_symbols = null;
    private GenericArray<string> parents;
    private GenericArray<string> children;
    private GenericArray<string> all_children;
    public string   name { get; private set; }
    public string   uri { get; private set; }
    public string   display_name { get; private set; }
    public string   doc { get; private set; }
    
    private Symbol(string uri, string name, string display_name, string doc, 
                GenericArray<string> parents, GenericArray<string> children, 
                GenericArray<string> all_children){
        this.name = name;
        this.uri = uri;
        this.display_name = display_name;
        this.doc = doc;
        this.parents = parents;
        this.children = children;
        this. all_children = all_children;
    }
    
    public List<Symbol> get_parents()
    {
       var results = new List<Symbol>();
       for (int i = 0; i < parents.length; i++){
            results.append(all_symbols.lookup(parents[i]));
       }
       return results;
    }
    
    public List<Symbol> get_children()
    {
        var results = new List<Symbol>();
        for (int i = 0; i < children.length; i++){
            results.append(all_symbols.lookup(children[i]));
        }
        return results;
    }
    
    public List<Symbol> get_all_children()
    {
        var results = new List<Symbol>();
        for (int i = 0; i < all_children.length; i++){
            results.append(all_symbols.lookup(all_children[i]));
        }
        return results;
    }
    
    public bool is_a(Symbol symbol)
    {
        for (int i = 0; i < parents.length; i++){
            if (symbol.uri == parents[i])
                return true;
        }
        return false;
    }
    
    public string to_string()
    {
        return this.uri;
    }
    
    public void register()
    {
        if (all_symbols == null)
            all_symbols = new HashTable<string, Symbol>(str_hash, str_equal);
        all_symbols.insert(uri, this);
    }
    
    public static Symbol from_uri(string uri)
    {
        return all_symbols.lookup(uri);
    }
}
