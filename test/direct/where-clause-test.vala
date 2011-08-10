/* where-clause-test.vala
 *
 * Copyright © 2011 Collabora Ltd.
 *             By Siegfried-Angel Gevatter Pujals <siegfried@gevatter.com>
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

using Zeitgeist;

void main (string[] args)
{
    Test.init (ref args);

    // Do not abort on warning()s.
    Log.set_always_fatal (LogLevelFlags.LEVEL_CRITICAL);

    Test.add_func ("/WhereClause/basic", basic_test);
    Test.add_func ("/WhereClause/nested", nested_test);
    Test.add_func ("/WhereClause/nested_negation", nested_negation_test);
    Test.add_func ("/WhereClause/text_condition", text_condition_test);

    Test.run ();
}

public void basic_test ()
{
    WhereClause where;

    where = new WhereClause (WhereClause.Type.AND);
    where.add ("1st condition");
    where.add ("2nd condition");
    assert (where.get_sql_conditions () == "(1st condition AND 2nd condition)");

    where = new WhereClause (WhereClause.Type.OR);
    where.add ("1st condition");
    where.add ("2nd condition");
    assert (where.get_sql_conditions () == "(1st condition OR 2nd condition)");

    where = new WhereClause (WhereClause.Type.AND, true);
    where.add ("some condition");
    assert (where.get_sql_conditions () == "NOT (some condition)");
}

public void nested_test ()
{
    var where = new WhereClause (WhereClause.Type.AND);
    where.add ("1st condition", "arg1");

    var subwhere = new WhereClause (WhereClause.Type.OR);
    {
        var args = new GenericArray<string> ();
        args.add ("arg2");
        args.add ("arg3");
        subwhere.add_with_array ("2nd condition", args);
        subwhere.add ("3rd condition");
    }

    where.extend (subwhere);
    where.add ("last condition");

    assert (where.get_sql_conditions () == "(1st condition AND (2nd " +
        "condition OR 3rd condition) AND last condition)");

    {
        var args = where.get_bind_arguments ();
        assert (args.length == 3);
        assert (args[0] == "arg1");
        assert (args[1] == "arg2");
        assert (args[2] == "arg3");
    }
}

public void nested_negation_test ()
{
    var where = new WhereClause (WhereClause.Type.OR);
    where.add ("cond1", "arg1");

    var subwhere = new WhereClause (WhereClause.Type.OR, true);
    subwhere.add ("cond2");

    where.extend (subwhere);
    where.add ("cond3");

    assert (where.get_sql_conditions () == "(cond1 OR NOT (cond2) " +
        "OR cond3)");
}

public void text_condition_test ()
{
    WhereClause where;

    // Plain
    where = new WhereClause (WhereClause.Type.AND);
    where.add_text_condition ("field1", "value1");
    assert (where.get_sql_conditions () == "(field1 = ?)");
    assert (where.get_bind_arguments ().length == 1);
    assert (where.get_bind_arguments ()[0] == "value1");

    // Negation
    where = new WhereClause (WhereClause.Type.AND);
    where.add_text_condition ("f2", "v2", false, true);
    assert (where.get_sql_conditions () == "(f2 != ?)");

    // FIXME: test LIKE stuff...
}
