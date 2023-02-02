#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#
from future import standard_library
standard_library.install_aliases()
from past.utils import old_div
from apiv2.forms import API_SORT_OPTIONS_MAP
from utils.similarity_utilities import api_search as similarity_api_search
from utils.search import SearchEngineException, get_search_engine
from utils.search.search_sounds import parse_weights_parameter
from similarity.client import SimilarityException
from .exceptions import ServerErrorException, BadRequestException, NotFoundException
from urllib.parse import unquote


def merge_all(search_form, target_file=None, extra_parameters=None):
    """
    Merge all strategy will get all results from solr and all results from gaia and then combine the ids
    in a unique list. The advantage of this strategy is that it returns the exact total number of matches for the query.
    The disadvantage is that depending on the query it can become really slow, and sometimes throwing timeouts.
    """

    if not extra_parameters:
        extra_parameters = dict()
    solr_page_size = extra_parameters.get('cs_solr_page_size', 500)
    max_solr_pages = extra_parameters.get('cs_max_solr_pages', 10)
    gaia_page_size = extra_parameters.get('cs_gaia_page_size', 9999999)  # We can get ALL gaia results at once
    max_gaia_pages = extra_parameters.get('cs_max_gaia_pages', 1)

    # Get all gaia results
    gaia_ids, gaia_count, distance_to_target_data, note = get_gaia_results(search_form, target_file, page_size=gaia_page_size, max_pages=max_gaia_pages)

    # Get 'max_pages' pages of size 'page_size' from solr results
    solr_ids, solr_count = get_solr_results(search_form, page_size=solr_page_size, max_pages=max_solr_pages)

    if len(solr_ids) == solr_count and len(gaia_ids) == gaia_count:
        # Got complete results, maybe we should log that?
        pass

    if search_form.cleaned_data['target'] or target_file:
        # Combined search, sort by gaia_ids
        results_a = gaia_ids
        results_b = solr_ids
    else:
        # Combined search, sort by solr ids
        results_a = solr_ids
        results_b = gaia_ids

    # Combine results
    results_b_set = set(results_b)
    combined_ids = [id for id in results_a if id in results_b_set]
    combined_count = len(combined_ids)
    return combined_ids[(search_form.cleaned_data['page'] - 1) * search_form.cleaned_data['page_size']:search_form.cleaned_data['page'] * search_form.cleaned_data['page_size']], \
           combined_count, distance_to_target_data, None, note, None, None


def filter_both(search_form, target_file=None, extra_parameters=None):
    """
    Filter both strategy will first get either some results from solr and then check if returned results are also
    valid results in a gaia query, or the other way around.
    In gaia and solr we can restrict the query to a particular set of results, but there are limitations both in the
    length of the resulting url and in the number of OR clauses that solr can support.
    """

    if not extra_parameters:
        extra_parameters = dict()
    solr_filter_id_block_size = extra_parameters.get('cs_solr_filter_id_block_size', 350)
    solr_filter_id_max_pages = extra_parameters.get('cs_solr_filter_id_max_pages', 7)
    solr_max_pages = extra_parameters.get('cs_max_solr_pages', 7)
    solr_page_size = extra_parameters.get('cs_solr_page_size', 1000)
    gaia_filter_id_block_size = extra_parameters.get('cs_gaia_filter_id_block_size', 350)
    gaia_filter_id_max_pages = extra_parameters.get('cs_gaia_filter_id_max_pages', 7)
    gaia_max_pages = extra_parameters.get('cs_max_gaia_pages', 1)
    gaia_page_size = extra_parameters.get('cs_gaia_page_size', 9999999)  # We can get ALL gaia results at once

    if search_form.cleaned_data['target'] or target_file:
        # First search into gaia and then into solr (get all gaia results)
        gaia_ids, gaia_count, distance_to_target_data, note = get_gaia_results(search_form, target_file, page_size=gaia_page_size, max_pages=gaia_max_pages)
        valid_ids_pages = [gaia_ids[i:i+solr_filter_id_block_size] for i in range(0, len(gaia_ids), solr_filter_id_block_size) if (old_div(i,solr_filter_id_block_size)) < solr_filter_id_max_pages]
        solr_ids = list()
        search_engine = get_search_engine()
        for valid_ids_page in valid_ids_pages:
            page_solr_ids, solr_count = get_solr_results(search_form, page_size=len(valid_ids_page), max_pages=1, valid_ids=valid_ids_page, search_engine=search_engine)
            solr_ids += page_solr_ids

        if gaia_count <= solr_filter_id_block_size * solr_filter_id_max_pages:
            # Got complete results, maybe we should log that?
            #print 'COMPLETE results (starting with gaia)'
            pass
    else:
        # First search into solr and then into gaia
        # These queries are SLOW because we need to get many pages from solr
        solr_ids, solr_count = get_solr_results(search_form, page_size=solr_page_size, max_pages=solr_max_pages)

        # Now we should split solr ids in blocks and iteratively query gaia restricting the results to those ids
        # present in the current block. However given that gaia results can be retrieved
        # all at once very quickly, we optimize this bit by retrieving them all at once and avoiding many requests
        # to similarity server.
        gaia_ids, gaia_count, distance_to_target_data, note = get_gaia_results(search_form, target_file, page_size=gaia_page_size, max_pages=gaia_max_pages)
        '''
        # That would be the code without the optimization:
        valid_ids_pages = [solr_ids[i:i+gaia_filter_id_block_size] for i in range(0, len(solr_ids), gaia_filter_id_block_size) if (i/gaia_filter_id_block_size) < gaia_filter_id_max_pages]
        gaia_ids = list()
        distance_to_target_data = None
        note = None
        for valid_ids_page in valid_ids_pages:
            page_gaia_ids, page_gaia_count, page_distance_to_target_data, note = get_gaia_results(search_form, target_file, page_size=len(valid_ids_page), max_pages=1, valid_ids=valid_ids_page)
            gaia_ids += page_gaia_ids
        '''
        if solr_count <= solr_page_size * solr_max_pages and gaia_count < gaia_page_size * gaia_max_pages:
            # Got complete results, maybe we should log that?
            #print 'COMPLETE results (starting with solr)'
            pass


    if search_form.cleaned_data['target'] or target_file:
        # Combined search, sort by gaia_ids
        results_a = gaia_ids
        results_b = solr_ids
    else:
        # Combined search, sort by solr ids
        results_a = solr_ids
        results_b = gaia_ids

    # Combine results
    results_b_set = set(results_b)
    combined_ids = [id for id in results_a if id in results_b_set]
    combined_count = len(combined_ids)
    return combined_ids[(search_form.cleaned_data['page'] - 1) * search_form.cleaned_data['page_size']:search_form.cleaned_data['page'] * search_form.cleaned_data['page_size']], \
           combined_count, distance_to_target_data, None, note, None, None


def merge_optimized(search_form, target_file=None, extra_parameters=None):
    """
    Filter both strategy will first get either some results from solr and then check if returned results are also
    valid results in a gaia query, or the other way around.
    In gaia and solr we can restrict the query to a particular set of results, but there are limitations both in the
    length of the resulting url and in the number of OR clauses that solr can support.
    """

    if not extra_parameters:
        extra_parameters = dict()
    solr_filter_id_block_size = extra_parameters.get('cs_solr_filter_id_block_size', 350)
    solr_filter_id_max_pages = extra_parameters.get('cs_solr_filter_id_max_pages', 7)
    solr_max_requests = extra_parameters.get('cs_max_solr_requests', 20)
    solr_page_size = extra_parameters.get('cs_solr_page_size', 200)
    gaia_max_pages = extra_parameters.get('cs_max_gaia_pages', 1)
    gaia_page_size = extra_parameters.get('cs_gaia_page_size', 9999999)  # We can get ALL gaia results at once

    num_requested_results = search_form.cleaned_data['page_size']
    params_for_next_page = dict()

    debug_note = ''

    if search_form.cleaned_data['target'] or target_file:
        # First search into gaia and get all results that have not been checked in previous calls (indicated in request parameter 'cs_lcvidp')
        last_checked_valid_id_position = extra_parameters.get('cs_lcvidp', 0)
        if last_checked_valid_id_position < 0:
            last_checked_valid_id_position = 0
        gaia_ids, gaia_count, distance_to_target_data, note = get_gaia_results(search_form, target_file, page_size=gaia_page_size, max_pages=gaia_max_pages, offset=last_checked_valid_id_position)
        if len(gaia_ids):
            # Now divide gaia results in blocks of "solr_filter_id_block_size" results and iteratively query solr limiting the
            # results to those ids in the common block to obtain common results for the search.
            # Once we get as many results as "num_requested_results" or we exceed a maximum number
            # of iterations (solr_filter_id_max_pages), return what we got and update 'cs_lcvidp' parameter for further calls.
            valid_ids_pages = [gaia_ids[i:i+solr_filter_id_block_size] for i in range(0, len(gaia_ids), solr_filter_id_block_size)]
            solr_ids = list()
            checked_gaia_ids = list()
            search_engine = get_search_engine()
            for count, valid_ids_page in enumerate(valid_ids_pages):
                page_solr_ids, solr_count = get_solr_results(search_form, page_size=len(valid_ids_page), max_pages=1, valid_ids=valid_ids_page, search_engine=search_engine)
                solr_ids += page_solr_ids
                checked_gaia_ids += valid_ids_page
                if len(solr_ids) >= num_requested_results:
                    debug_note = 'Found enough results in %i solr requests' % (count + 1)
                    #print 'Did %i requests to solr' % (count + 1)
                    break
                if count + 1 > solr_filter_id_max_pages:
                    debug_note = 'Did %i solr requests (still not enough results)' % (count + 1)
                    #print 'Too many requests and not enough results'
                    break

            combined_ids = list()
            for index, sid in enumerate(checked_gaia_ids):
                if sid in solr_ids:
                    combined_ids.append(sid)
                new_last_checked_valid_id_position = index + 1
                if len(combined_ids) == num_requested_results:
                    break

            if len(checked_gaia_ids) == len(gaia_ids):
                params_for_next_page['no_more_results'] = True
            params_for_next_page['cs_lcvidp'] = last_checked_valid_id_position + new_last_checked_valid_id_position
        else:
            # No more gaia ids to check against solr, no more possible results!
            combined_ids = list()
            distance_to_target_data = dict()
            note = None
            params_for_next_page['no_more_results'] = True

    else:
        # First search into gaia to obtain a list of all sounds that match content-based query parameters
        gaia_ids, gaia_count, distance_to_target_data, note = get_gaia_results(search_form, target_file, page_size=gaia_page_size, max_pages=gaia_max_pages)
        last_retrieved_solr_id_pos = extra_parameters.get('cs_lrsidp', 0)
        if last_retrieved_solr_id_pos < 0:
            last_retrieved_solr_id_pos = 0

        if len(gaia_ids) < solr_filter_id_block_size:
            # optimization, if there are few gaia_ids, we can get all results in one query
            solr_ids, solr_count = get_solr_results(search_form, page_size=len(gaia_ids), max_pages=1, valid_ids=gaia_ids, offset=last_retrieved_solr_id_pos)
            combined_ids = solr_ids[:num_requested_results]
            params_for_next_page['cs_lrsidp'] = last_retrieved_solr_id_pos + num_requested_results
            if len(combined_ids) < num_requested_results:
                params_for_next_page['no_more_results'] = True
        else:
            # Now query solr starting at the last retrieved solr result position (parameter 'cs_lrsidp') and iteratively combine the results of
            # each page of the query with gaia ids. Once we reach the desired  "num_requested_results", return what we got and
            # update 'cs_lrsidp' parameter for further queries. Set a maximum number of iterations (solr_max_requests) to prevent a virtually
            # infinite query if not enough results are found (num_requested_results is not reached).
            combined_ids = list()
            new_last_retrieved_solr_id_pos = last_retrieved_solr_id_pos
            stop_main_for_loop = False
            n_requests_made = 0
            for i in range(0, solr_max_requests):
                if stop_main_for_loop:
                    continue
                offset = last_retrieved_solr_id_pos + i * solr_page_size
                solr_ids, solr_count = get_solr_results(search_form, page_size=solr_page_size, max_pages=1, offset=offset)
                n_requests_made += 1
                common_ids = list(set(solr_ids).intersection(gaia_ids))
                for index, sid in enumerate(solr_ids):
                    new_last_retrieved_solr_id_pos += 1
                    if sid in common_ids:
                        combined_ids.append(sid)
                    if len(combined_ids) == num_requested_results:
                        stop_main_for_loop = True
                        break
                    if new_last_retrieved_solr_id_pos == solr_count:
                        params_for_next_page['no_more_results'] = True
                        stop_main_for_loop = True
                        break
            if n_requests_made == solr_max_requests and len(combined_ids) < num_requested_results:
                debug_note = 'Did %i solr requests (still not enough results)' % n_requests_made
                #print 'Too many requests and not enough results'
            else:
                debug_note = 'Found enough results in %i solr requests' % n_requests_made
                #print 'Did %i requests to solr' % n_requests_made
            params_for_next_page['cs_lrsidp'] = new_last_retrieved_solr_id_pos

    # Combine results
    return combined_ids, len(combined_ids), distance_to_target_data, None, note, params_for_next_page, debug_note


def get_gaia_results(search_form, target_file, page_size, max_pages, start_page=1, valid_ids=None, offset=None):
    gaia_ids = list()
    gaia_count = None
    distance_to_target_data = dict()
    note = None

    try:
        current_page = start_page
        n_page_requests = 1
        # Iterate over gaia result pages
        while (len(gaia_ids) < gaia_count or gaia_count == None) and n_page_requests <= max_pages:
            if not offset:
                offset = (current_page - 1) * page_size
            results, count, note = similarity_api_search(target=search_form.cleaned_data['target'],
                                                         filter=search_form.cleaned_data['descriptors_filter'],
                                                         num_results=page_size,
                                                         offset=offset,
                                                         target_file=target_file,
                                                         in_ids=valid_ids)

            gaia_ids += [id[0] for id in results]
            gaia_count = count
            if search_form.cleaned_data['target'] or target_file:
                # Save sound distance to target into so it can be later used in the view class and added to results
                distance_to_target_data.update(dict(results))

            #print 'Gaia page %i (total %i sounds)' % (current_page, gaia_count)
            current_page += 1
            n_page_requests += 1

    except SimilarityException as e:
        if e.status_code == 500:
            raise ServerErrorException(msg=str(e))
        elif e.status_code == 400:
            raise BadRequestException(msg=str(e))
        elif e.status_code == 404:
            raise NotFoundException(msg=str(e))
        else:
            raise ServerErrorException(msg='Similarity server error: %s' % str(e))
    except Exception as e:
        raise ServerErrorException(msg='The similarity server could not be reached or some unexpected error occurred.')

    return gaia_ids, gaia_count, distance_to_target_data, note


def get_solr_results(search_form, page_size, max_pages, start_page=1, valid_ids=None, search_engine=None, offset=None):
    if not search_engine:
        search_engine = get_search_engine()

    query_filter = search_form.cleaned_data['filter']
    if valid_ids:
        # Update solr filter to only return results in valid ids
        ids_filter = 'id:(' + ' OR '.join([str(item) for item in valid_ids]) + ')'
        if query_filter:
            query_filter += ' %s' % ids_filter
        else:
            query_filter = ids_filter

    solr_ids = []
    solr_count = None

    try:
        current_page = start_page
        n_page_requests = 1
        # Iterate over solr result pages
        while (len(solr_ids) < solr_count or solr_count == None) and n_page_requests <= max_pages:
            # We need to convert the sort parameter to standard sorting options from
            # settings.SEARCH_SOUNDS_SORT_OPTION_X. Therefore here we convert to the standard names and later
            # the get_search_engine().search_sounds() function will convert it back to search engine meaningful names
            processed_sort = API_SORT_OPTIONS_MAP[search_form.cleaned_data['sort'][0]]
            result = search_engine.search_sounds(
                textual_query=unquote(search_form.cleaned_data['query'] or ""),
                query_filter=unquote(query_filter or ""),
                query_fields=parse_weights_parameter(search_form.cleaned_data['weights']),
                sort=processed_sort,
                offset=(current_page - 1) * page_size,
                num_sounds=page_size,
                group_by_pack=False

            )
            solr_ids += [element['id'] for element in result.docs]
            solr_count = result.num_found

            #print 'Solr page %i (total %i sounds)' % (current_page, solr_count)
            current_page += 1
            n_page_requests += 1

    except SearchEngineException as e:
        raise ServerErrorException(msg='Search server error: %s' % str(e))
    except Exception as e:
        raise ServerErrorException(msg='The search server could not be reached or some unexpected error occurred.')
    return solr_ids, solr_count
