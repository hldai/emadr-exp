import numpy as np
import scipy.spatial
import ioutils


def load_gold_label_file(label_file):
    fin = open(label_file, 'rb')
    label_dict = dict()
    for line in fin:
        vals = line.strip().split('\t')
        if len(vals) < 3 or not vals[0][-1].isdigit():
            continue
        label_dict[vals[0]] = vals[1]
    fin.close()

    return label_dict


def load_mid_eid_file(file_name):
    print 'loading ', file_name
    fin = open(file_name, 'rb')
    num_mids = np.fromfile(fin, '>i4', 1)
    print num_mids, 'mids'
    id_len = 8
    mid_eid_dict = dict()
    for i in xrange(num_mids):
        mid = ioutils.read_str_with_fixed_len(fin, id_len)
        eid = ioutils.read_str_with_fixed_len(fin, id_len)
        mid_eid_dict[mid] = eid
    fin.close()
    print 'done'
    return mid_eid_dict


def add_gold_label(vec_train_file, gold_label_file, mid_eid_file, dst_file):
    mid_eid_dict = load_mid_eid_file(mid_eid_file)
    label_dict = load_gold_label_file(gold_label_file)

    vec_dim = 100

    nil_cnt = 0
    miss_cnt = 0
    fh_cnt = 0
    tmp_fout = open('e:/dc/el/tmp_result.txt', 'wb')
    fin = open(vec_train_file, 'rb')
    num_docs = np.fromfile(fin, '>i4', 1)
    print num_docs
    fout = open(dst_file, 'wb')
    np.asarray([num_docs, vec_dim], np.int32).tofile(fout)
    for i in xrange(num_docs):
        doc_id = ioutils.read_str_with_byte_len(fin)
        doc_vec = np.fromfile(fin, '>f4', vec_dim)

        doc_vec.astype(np.float32).tofile(fout)

        mention_infos = list()
        num_mentions = np.fromfile(fin, '>i4', 1)
        for j in xrange(num_mentions):
            qid = ioutils.read_str_with_byte_len(fin)
            # print qid
            # if qid == '':
            #     print doc_id, j, num_mentions
            gold_label = label_dict[qid]
            # gold_label = 'NIL'
            if gold_label.startswith('NIL'):
                nil_cnt += 1

            num_candidates = np.fromfile(fin, '>i4', 1)
            hit_idx = -1
            commonness = list()
            candidate_vecs = list()
            eids = list()
            for k in xrange(num_candidates):
                mid = ioutils.read_str_with_fixed_len(fin, 8)
                eid = mid_eid_dict.get(mid, 'NILL')

                if k == 0 and eid != 'NILL':
                    tmp_fout.write(qid + '\t' + eid + '\n')
                if eid == gold_label:
                    hit_idx = k

                cur_com = np.fromfile(fin, '>f4', 1)
                # print cur_com
                commonness.append(cur_com)
                vec = np.fromfile(fin, '>f4', vec_dim)
                candidate_vecs.append(vec.astype(np.float32))
                eids.append(eid)

            if hit_idx == -1:
                miss_cnt += 1
            else:
                # mention_infos.append((qid, hit_idx, candidate_vecs, eids))
                mention_infos.append((hit_idx, commonness, candidate_vecs))
                if hit_idx == 0:
                    fh_cnt += 1

        # print len(mention_infos)
        np.asarray([len(mention_infos)], np.int32).tofile(fout)
        for mention_info in mention_infos:
            # io_utils.write_str_with_byte_len(mention_info[0], fout)
            np.asarray([len(mention_info[1])], np.int32).tofile(fout)
            np.asarray([mention_info[0]], np.int32).tofile(fout)
            np.asarray(mention_info[1], np.float32).tofile(fout)
            for vec in mention_info[2]:
                vec.tofile(fout)
            # for eid in mention_info[3]:
            #     io_utils.write_str_with_byte_len(eid, fout)
        # break
    fin.close()
    fout.close()
    tmp_fout.close()

    num_queries = len(label_dict)
    num_non_nil_queries = num_queries - nil_cnt
    print 'nil_cnt\tmiss_cnt\tfh_cnt\tnum_queries\tnum_non_nil_queries'
    print nil_cnt, miss_cnt, fh_cnt, num_queries, num_non_nil_queries
    print float(fh_cnt) / num_non_nil_queries
    print 1 - float(miss_cnt - nil_cnt) / num_non_nil_queries


def simple_link():
    year = 2010
    part = 'train'
    method = 3
    expand = ''
    # expand = '_exp'

    dataset_file = 'e:/dc/el/dwe_train/%d/%s_%d%s_wl.bin' % (year, part, method, expand)

    fin = open(dataset_file, 'rb')
    num_docs, dim = np.fromfile(fin, np.int32, 2)
    fh_cnt, tf_cnt, hit_cnt = 0, 0, 0
    cmn_lim = 0.03
    max_diff = 0
    min_cmn = 1
    avg = 0
    total_num_candidates = 0
    for i in xrange(num_docs):
        # doc_vec = np.fromfile(fin, '>f4', dim)
        doc_vec = np.fromfile(fin, np.float32, dim)
        num_mentions = np.fromfile(fin, np.int32, 1)
        for j in xrange(num_mentions):
            sims = list()
            score_list = list()

            # qid = io_utils.read_str_with_byte_len(fin)
            num_candidates = np.fromfile(fin, np.int32, 1)
            total_num_candidates += num_candidates
            idx = np.fromfile(fin, np.int32, 1)
            commonness = np.fromfile(fin, np.float32, num_candidates)
            if idx == 0:
                fh_cnt += 1

            if commonness[idx] > cmn_lim:
                tf_cnt += 1
            # print commonness[:5]
            candidate_vecs = list()
            for k in xrange(num_candidates):
                vec = np.fromfile(fin, np.float32, dim)
                candidate_vecs.append(vec)

                # print candidate_vecs[0]
            sys_idx = 0
            max_score = -1e5
            for k in xrange(num_candidates):
                # if k == 30:
                #     break

                sim = 1 - scipy.spatial.distance.cosine(doc_vec, candidate_vecs[k])

                sims.append(sim)
                # cur_score = 0.3 * commonness[k] + (1 - 0.3) * sim
                cur_score = 0.45 * commonness[k] + (1 - 0.45) * sim
                # cur_score = sim
                score_list.append((0.5 * commonness[k], (1 - 0.5) * sim))

                # if k == idx:
                #     print commonness[k], sim
                if cur_score > max_score:
                    sys_idx = k
                    max_score = cur_score

            if sys_idx == idx:
                if commonness[idx] - commonness[0] > max_diff:
                    max_diff = commonness[idx] - commonness[0]

                hit_cnt += 1
    fin.close()
    print '%d first hit: %d, hit: %d, acc: %f' % (tf_cnt, fh_cnt, hit_cnt, hit_cnt / 1020.)
    print avg
    print max_diff
    print min_cmn
    print total_num_candidates


def test():
    file0 = 'e:/el/link_result/query_results_clf_train_14.txt'
    file1 = 'e:/dc/el/tmp_result.txt'
    results = dict()
    fin = open(file0, 'rb')
    for line in fin:
        vals = line.strip().split()
        results[vals[0]] = vals[1]
    fin.close()

    fin = open(file1, 'rb')
    for line in fin:
        vals = line.strip().split()
        eid0 = results[vals[0]]
        if vals[1] != eid0:
            print vals[0], vals[1], eid0
    fin.close()


def main():
    year = 2010
    part = 'train'
    method = 3
    expand = ''
    # expand = '_exp'

    gold_label_file = ''
    if year == 2014 and part == 'train':
        gold_label_file = 'd:/data/el/LDC2015E20_EDL_2014/data/training/' \
                          'tac_kbp_2014_english_EDL_training_KB_links.tab'
    if year == 2014 and part == 'eval':
        gold_label_file = 'd:/data/el/LDC2015E20_EDL_2014/data/eval/' \
                          'tac_2014_kbp_english_EDL_evaluation_KB_links.tab'
    if year == 2010 and part == 'eval':
        gold_label_file = 'd:/data/el/LDC2015E19/data/2010/eval/' \
                          'tac_kbp_2010_english_entity_linking_evaluation_KB_links.tab'
    if year == 2010 and part == 'train':
        gold_label_file = 'd:/data/el/LDC2015E19/data/2010/training/' \
                          'tac_kbp_2010_english_entity_linking_training_KB_links.tab'
    if year == 2009 and part == 'eval':
        gold_label_file = 'd:/data/el/LDC2015E19/data/2009/eval/' \
                          'tac_kbp_2009_english_entity_linking_evaluation_KB_links.tab'

    # vec_file = 'e:/dc/el/dwe_train/tac_' + file_tag + '.bin'
    # dst_file = 'e:/dc/el/dwe_train/tac_' + file_tag + '_wl.bin'
    vec_file = 'e:/dc/el/dwe_train/%d/%s_%d%s.bin' % (year, part, method, expand)
    dst_file = 'e:/dc/el/dwe_train/%d/%s_%d%s_wl.bin' % (year, part, method, expand)

    mid_eid_file = 'd:/data/el/2014/mid_to_eid.ss'
    add_gold_label(vec_file, gold_label_file, mid_eid_file, dst_file)


if __name__ == '__main__':
    # main()
    simple_link()
    # test()
