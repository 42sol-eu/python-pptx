# encoding: utf-8

"""
Test suite for pptx.opc.package module
"""

from __future__ import absolute_import

import pytest

from mock import call, Mock, patch, PropertyMock

from pptx.opc.oxml import CT_Relationships
from pptx.opc.packuri import PACKAGE_URI, PackURI
from pptx.opc.package import (
    OpcPackage, Part, PartFactory, _Relationship, RelationshipCollection,
    Unmarshaller
)
from pptx.opc.pkgreader import PackageReader
from pptx.presentation import Package

from ..oxml.unitdata.text import an_hlinkClick, an_rPr
from ..unitutil import (
    cls_attr_mock, class_mock, instance_mock, loose_mock, method_mock
)


class DescribeOpcPackage(object):

    def it_can_open_a_pkg_file(self, PackageReader_, PartFactory_,
                               Unmarshaller_):
        # mockery ----------------------
        pkg_file = Mock(name='pkg_file')
        pkg_reader = PackageReader_.from_file.return_value
        # exercise ---------------------
        pkg = OpcPackage.open(pkg_file)
        # verify -----------------------
        PackageReader_.from_file.assert_called_once_with(pkg_file)
        Unmarshaller_.unmarshal.assert_called_once_with(pkg_reader, pkg,
                                                        PartFactory_)
        assert isinstance(pkg, OpcPackage)

    def it_initializes_its_rels_collection_on_first_reference(
            self, RelationshipCollection_):
        pkg = OpcPackage()
        rels = pkg.rels
        RelationshipCollection_.assert_called_once_with(PACKAGE_URI.baseURI)
        assert rels == RelationshipCollection_.return_value

    def it_can_add_a_relationship_to_a_part(self, pkg_with_rels_, rel_attrs_):
        reltype, target, rId = rel_attrs_
        pkg = pkg_with_rels_
        # exercise ---------------------
        pkg.load_rel(reltype, target, rId)
        # verify -----------------------
        pkg._rels.add_relationship.assert_called_once_with(
            reltype, target, rId, False
        )

    def it_can_establish_a_relationship_to_another_part(
            self, relate_to_part_fixture_):
        pkg, part_, reltype, rId = relate_to_part_fixture_
        _rId = pkg.relate_to(part_, reltype)
        pkg.rels.get_or_add.assert_called_once_with(reltype, part_)
        assert _rId == rId

    def it_can_provide_a_list_of_the_parts_it_contains(self):
        # mockery ----------------------
        parts = [Mock(name='part1'), Mock(name='part2')]
        pkg = OpcPackage()
        # verify -----------------------
        with patch.object(OpcPackage, 'iter_parts', return_value=parts):
            assert pkg.parts == [parts[0], parts[1]]

    def it_can_iterate_over_parts_by_walking_rels_graph(self):
        # +----------+       +--------+
        # | pkg_rels |-----> | part_1 |
        # +----------+       +--------+
        #      |               |    ^
        #      v               v    |
        #   external         +--------+
        #                    | part_2 |
        #                    +--------+
        part1, part2 = (Mock(name='part1'), Mock(name='part2'))
        part1.rels = [Mock(name='rel1', is_external=False, target_part=part2)]
        part2.rels = [Mock(name='rel2', is_external=False, target_part=part1)]
        pkg = OpcPackage()
        pkg._rels = [
            Mock(name='rel3', is_external=False, target_part=part1),
            Mock(name='rel3', is_external=True),
        ]
        # exercise ---------------------
        generated_parts = [part for part in pkg.iter_parts()]
        # verify -----------------------
        assert generated_parts == [part1, part2]

    def it_can_find_a_part_related_by_reltype(self, related_part_fixture_):
        pkg, reltype, related_part_ = related_part_fixture_
        related_part = pkg.part_related_by(reltype)
        pkg.rels.part_with_reltype.assert_called_once_with(reltype)
        assert related_part is related_part_

    def it_can_save_to_a_pkg_file(
            self, pkg_file_, PackageWriter_, parts, parts_):
        pkg = OpcPackage()
        pkg.save(pkg_file_)
        for part in parts_:
            part.before_marshal.assert_called_once_with()
        PackageWriter_.write.assert_called_once_with(
            pkg_file_, pkg._rels, parts_
        )

    # fixtures ---------------------------------------------

    @pytest.fixture
    def PackageReader_(self, request):
        return class_mock(request, 'pptx.opc.package.PackageReader')

    @pytest.fixture
    def PackageWriter_(self, request):
        return class_mock(request, 'pptx.opc.package.PackageWriter')

    @pytest.fixture
    def PartFactory_(self, request):
        return class_mock(request, 'pptx.opc.package.PartFactory')

    @pytest.fixture
    def parts(self, request, parts_):
        """
        Return a mock patching property OpcPackage.parts, reversing the
        patch after each use.
        """
        _patch = patch.object(
            OpcPackage, 'parts', new_callable=PropertyMock,
            return_value=parts_
        )
        request.addfinalizer(_patch.stop)
        return _patch.start()

    @pytest.fixture
    def parts_(self, request):
        part_ = instance_mock(request, Part, name='part_')
        part_2_ = instance_mock(request, Part, name='part_2_')
        return [part_, part_2_]

    @pytest.fixture
    def pkg(self, request):
        return OpcPackage()

    @pytest.fixture
    def pkg_file_(self, request):
        return loose_mock(request)

    @pytest.fixture
    def pkg_with_rels_(self, request, rels_):
        pkg = OpcPackage()
        pkg._rels = rels_
        return pkg

    @pytest.fixture
    def RelationshipCollection_(self, request):
        return class_mock(request, 'pptx.opc.package.RelationshipCollection')

    @pytest.fixture
    def rel_attrs_(self, request):
        reltype = 'http://rel/type'
        target_ = instance_mock(request, Part, name='target_')
        rId = 'rId99'
        return reltype, target_, rId

    @pytest.fixture
    def relate_to_part_fixture_(self, request, pkg, rels_, reltype):
        rId = 'rId99'
        rel_ = instance_mock(request, _Relationship, name='rel_', rId=rId)
        rels_.get_or_add.return_value = rel_
        pkg._rels = rels_
        part_ = instance_mock(request, Part, name='part_')
        return pkg, part_, reltype, rId

    @pytest.fixture
    def related_part_fixture_(self, request, rels_, reltype):
        related_part_ = instance_mock(request, Part, name='related_part_')
        rels_.part_with_reltype.return_value = related_part_
        pkg = OpcPackage()
        pkg._rels = rels_
        return pkg, reltype, related_part_

    @pytest.fixture
    def rels_(self, request):
        return instance_mock(request, RelationshipCollection)

    @pytest.fixture
    def reltype(self, request):
        return 'http://rel/type'

    @pytest.fixture
    def Unmarshaller_(self, request):
        return class_mock(request, 'pptx.opc.package.Unmarshaller')


class DescribePartLoadSaveInterface(object):

    def it_remembers_its_construction_state(self):
        partname, content_type, package, blob = (
            Mock(name='partname'), Mock(name='content_type'),
            Mock(name='package'), Mock(name='blob')
        )
        part = Part(partname, content_type, blob, package)
        assert part.partname == partname
        assert part.content_type == content_type
        assert part.blob == blob
        assert part.package == package

    def it_can_be_notified_after_unmarshalling_is_complete(self, part):
        part.after_unmarshal()

    def it_can_be_notified_before_marshalling_is_started(self, part):
        part.before_marshal()

    def it_allows_its_partname_to_be_changed(self, part):
        new_partname = PackURI('/ppt/presentation.xml')
        part.partname = new_partname
        assert part.partname == new_partname

    def it_can_load_a_relationship_during_package_open(
            self, part_with_rels_, rel_attrs_):
        # fixture ----------------------
        part, rels_ = part_with_rels_
        reltype, target, rId = rel_attrs_
        # exercise ---------------------
        part.load_rel(reltype, target, rId)
        # verify -----------------------
        rels_.add_relationship.assert_called_once_with(
            reltype, target, rId, False
        )

    # fixtures ---------------------------------------------

    @pytest.fixture
    def part(self):
        partname = PackURI('/foo/bar.xml')
        part = Part(partname, None, None)
        return part

    @pytest.fixture
    def part_with_rels_(self, request, part, rels_):
        part._rels = rels_
        return part, rels_

    @pytest.fixture
    def rel_attrs_(self, request):
        reltype = 'http://rel/type'
        target_ = instance_mock(request, Part, name='target_')
        rId = 'rId99'
        return reltype, target_, rId

    @pytest.fixture
    def rels_(self, request):
        return instance_mock(request, RelationshipCollection)


class DescribePartRelsProxyInterface(object):

    def it_has_a_rels_collection_initialized_on_first_reference(
            self, RelationshipCollection_):
        partname = PackURI('/foo/bar.xml')
        part = Part(partname, None, None)
        assert part.rels is RelationshipCollection_.return_value
        RelationshipCollection_.assert_called_once_with(partname.baseURI)

    def it_can_establish_a_relationship_to_another_part(
            self, relate_to_part_fixture_):
        # fixture ----------------------
        part, related_part_, reltype, rId = relate_to_part_fixture_
        # exercise ---------------------
        _rId = part.relate_to(related_part_, reltype)
        # verify -----------------------
        part.rels.get_or_add.assert_called_once_with(reltype, related_part_)
        assert _rId == rId

    def it_can_establish_an_external_relationship(
            self, relate_to_url_fixture_):
        part, url, reltype, rId = relate_to_url_fixture_
        _rId = part.relate_to(url, reltype, is_external=True)
        part.rels.get_or_add_ext_rel.assert_called_once_with(reltype, url)
        assert _rId == rId

    def it_can_drop_a_relationship(self, part_with_rels_to_drop_):
        part, rId, rId_2, rId_3 = part_with_rels_to_drop_
        part.drop_rel(rId)    # this one has ref count of 2, don't drop
        part.drop_rel(rId_2)  # this one has ref count of 1, drop
        part.drop_rel(rId_3)  # this one has ref count of 0, drop
        assert part.rels.__delitem__.call_args_list == [
            call(rId_2), call(rId_3)
        ]

    def it_can_find_a_part_related_by_reltype(self, related_part_fixture_):
        part, reltype, related_part_ = related_part_fixture_
        related_part = part.part_related_by(reltype)
        part.rels.part_with_reltype.assert_called_once_with(reltype)
        assert related_part is related_part_

    def it_can_find_the_target_ref_of_an_external_relationship(
            self, target_ref_fixture_):
        part, rId, url = target_ref_fixture_
        _url = part.target_ref(rId)
        assert _url == url

    # fixtures ---------------------------------------------

    @pytest.fixture
    def part(self):
        partname = PackURI('/foo/bar.xml')
        part = Part(partname, None, None)
        return part

    @pytest.fixture
    def part_with_rels_to_drop_(self, request, part, rels_):
        rId, rId_2, rId3 = 'rId1', 'rId2', 'rId3'
        _element = (
            an_rPr().with_nsdecls('a', 'r')
                    .with_child(an_hlinkClick().with_rId(rId))
                    .with_child(an_hlinkClick().with_rId(rId))
                    .with_child(an_hlinkClick().with_rId(rId_2))
                    .element
        )
        part._element = _element
        part._rels = rels_
        return part, rId, rId_2, rId3

    @pytest.fixture
    def RelationshipCollection_(self, request):
        return class_mock(request, 'pptx.opc.package.RelationshipCollection')

    @pytest.fixture
    def relate_to_part_fixture_(self, request, part, reltype):
        rId = 'rId99'
        related_part_ = instance_mock(request, Part, name='related_part_')
        rels_ = instance_mock(request, RelationshipCollection, name='rels_')
        rel_ = instance_mock(request, _Relationship, name='rel_', rId=rId)
        rels_.get_or_add.return_value = rel_
        part._rels = rels_
        return part, related_part_, reltype, rId

    @pytest.fixture
    def relate_to_url_fixture_(self, request, part, reltype):
        rId = 'rId21'
        url = 'https://github.com/scanny/python-pptx'
        rels_ = instance_mock(request, RelationshipCollection, name='rels_')
        rels_.get_or_add_ext_rel.return_value = rId
        part._rels = rels_
        return part, url, reltype, rId

    @pytest.fixture
    def related_part_fixture_(self, request, part, reltype):
        related_part_ = instance_mock(request, Part, name='related_part_')
        rels_ = instance_mock(request, RelationshipCollection, name='rels_')
        rels_.part_with_reltype.return_value = related_part_
        part._rels = rels_
        return part, reltype, related_part_

    @pytest.fixture
    def reltype(self):
        return 'http:/rel/type'

    @pytest.fixture
    def rels_(self, request):
        return instance_mock(request, RelationshipCollection)

    @pytest.fixture
    def target_ref_fixture_(self, request, part):
        rId = 'rId246'
        url = 'https://github.com/scanny/python-pptx'
        rels = RelationshipCollection(None)
        rels.add_relationship(None, url, rId, is_external=True)
        part._rels = rels
        return part, rId, url


class DescribePartFactory(object):

    def it_constructs_custom_part_type_for_registered_content_types(
            self, part_args_, CustomPartClass_, part_of_custom_type_):
        # fixture ----------------------
        partname, content_type, pkg, blob = part_args_
        # exercise ---------------------
        PartFactory.part_type_for[content_type] = CustomPartClass_
        part = PartFactory(partname, content_type, pkg, blob)
        # verify -----------------------
        CustomPartClass_.load.assert_called_once_with(
            partname, content_type, pkg, blob
        )
        assert part is part_of_custom_type_

    def it_constructs_part_using_default_class_when_no_custom_registered(
            self, part_args_2_, DefaultPartClass_, part_of_default_type_):
        partname, content_type, pkg, blob = part_args_2_
        part = PartFactory(partname, content_type, pkg, blob)
        DefaultPartClass_.load.assert_called_once_with(
            partname, content_type, pkg, blob
        )
        assert part is part_of_default_type_

    # fixtures ---------------------------------------------

    @pytest.fixture
    def part_of_custom_type_(self, request):
        return instance_mock(request, Part)

    @pytest.fixture
    def CustomPartClass_(self, request, part_of_custom_type_):
        CustomPartClass_ = Mock(name='CustomPartClass', spec=Part)
        CustomPartClass_.load.return_value = part_of_custom_type_
        return CustomPartClass_

    @pytest.fixture
    def part_of_default_type_(self, request):
        return instance_mock(request, Part)

    @pytest.fixture
    def DefaultPartClass_(self, request, part_of_default_type_):
        DefaultPartClass_ = cls_attr_mock(
            request, PartFactory, 'default_part_type'
        )
        DefaultPartClass_.load.return_value = part_of_default_type_
        return DefaultPartClass_

    @pytest.fixture
    def part_args_(self, request):
        partname_ = PackURI('/foo/bar.xml')
        content_type_ = 'content/type'
        pkg_ = instance_mock(request, Package, name="pkg_")
        blob_ = b'blob_'
        return partname_, content_type_, pkg_, blob_

    @pytest.fixture
    def part_args_2_(self, request):
        partname_2_ = PackURI('/bar/foo.xml')
        content_type_2_ = 'foobar/type'
        pkg_2_ = instance_mock(request, Package, name="pkg_2_")
        blob_2_ = b'blob_2_'
        return partname_2_, content_type_2_, pkg_2_, blob_2_


class Describe_Relationship(object):

    def it_remembers_construction_values(self):
        # test data --------------------
        rId = 'rId9'
        reltype = 'reltype'
        target = Mock(name='target_part')
        external = False
        # exercise ---------------------
        rel = _Relationship(rId, reltype, target, None, external)
        # verify -----------------------
        assert rel.rId == rId
        assert rel.reltype == reltype
        assert rel.target_part == target
        assert rel.is_external == external

    def it_should_raise_on_target_part_access_on_external_rel(self):
        rel = _Relationship(None, None, None, None, external=True)
        with pytest.raises(ValueError):
            rel.target_part

    def it_should_have_target_ref_for_external_rel(self):
        rel = _Relationship(None, None, 'target', None, external=True)
        assert rel.target_ref == 'target'

    def it_should_have_relative_ref_for_internal_rel(self):
        """
        Internal relationships (TargetMode == 'Internal' in the XML) should
        have a relative ref, e.g. '../slideLayouts/slideLayout1.xml', for
        the target_ref attribute.
        """
        part = Mock(name='part', partname=PackURI('/ppt/media/image1.png'))
        baseURI = '/ppt/slides'
        rel = _Relationship(None, None, part, baseURI)  # external=False
        assert rel.target_ref == '../media/image1.png'


class DescribeRelationshipCollection(object):

    def it_has_a_len(self):
        rels = RelationshipCollection(None)
        assert len(rels) == 0

    def it_supports_indexed_access(self):
        rels = RelationshipCollection(None)
        try:
            rels[0]
        except TypeError:
            msg = 'RelationshipCollection does not support indexed access'
            pytest.fail(msg)
        except IndexError:
            pass

    def it_has_dict_style_lookup_of_rel_by_rId(self):
        rel = Mock(name='rel', rId='foobar')
        rels = RelationshipCollection(None)
        rels._rels.append(rel)
        assert rels['foobar'] == rel

    def it_should_raise_on_failed_lookup_by_rId(self):
        rel = Mock(name='rel', rId='foobar')
        rels = RelationshipCollection(None)
        rels._rels.append(rel)
        with pytest.raises(KeyError):
            rels['barfoo']

    def it_can_add_a_relationship(self, _Relationship_):
        baseURI, rId, reltype, target, external = (
            'baseURI', 'rId9', 'reltype', 'target', False
        )
        rels = RelationshipCollection(baseURI)
        rel = rels.add_relationship(reltype, target, rId, external)
        _Relationship_.assert_called_once_with(rId, reltype, target, baseURI,
                                               external)
        assert rels[0] == rel
        assert rel == _Relationship_.return_value

    def it_can_add_an_external_relationship(self, add_ext_rel_fixture_):
        rels, reltype, url = add_ext_rel_fixture_
        rId = rels.get_or_add_ext_rel(reltype, url)
        rel = rels[rId]
        assert rel.is_external
        assert rel.target_ref == url
        assert rel.reltype == reltype

    def it_should_return_an_existing_one_if_it_matches(
            self, add_matching_ext_rel_fixture_):
        rels, reltype, url, rId = add_matching_ext_rel_fixture_
        _rId = rels.get_or_add_ext_rel(reltype, url)
        assert _rId == rId
        assert len(rels) == 1

    def it_can_compose_rels_xml(self, rels, rels_elm):
        # exercise ---------------------
        rels.xml
        # trace ------------------------
        print('Actual calls:\n%s' % rels_elm.mock_calls)
        # verify -----------------------
        expected_rels_elm_calls = [
            call.add_rel('rId1', 'http://rt-hyperlink', 'http://some/link',
                         True),
            call.add_rel('rId2', 'http://rt-image', '../media/image1.png',
                         False),
            call.xml()
        ]
        assert rels_elm.mock_calls == expected_rels_elm_calls

    # fixtures ---------------------------------------------

    @pytest.fixture
    def add_ext_rel_fixture_(self, reltype, url):
        rels = RelationshipCollection(None)
        return rels, reltype, url

    @pytest.fixture
    def add_matching_ext_rel_fixture_(self, request, reltype, url):
        rId = 'rId369'
        rels = RelationshipCollection(None)
        rels.add_relationship(reltype, url, rId, is_external=True)
        return rels, reltype, url, rId

    @pytest.fixture
    def _Relationship_(self, request):
        return class_mock(request, 'pptx.opc.package._Relationship')

    @pytest.fixture
    def rels(self):
        """
        Populated RelationshipCollection instance that will exercise the
        rels.xml property.
        """
        rels = RelationshipCollection('/baseURI')
        rels.add_relationship(
            reltype='http://rt-hyperlink', target='http://some/link',
            rId='rId1', is_external=True
        )
        part = Mock(name='part')
        part.partname.relative_ref.return_value = '../media/image1.png'
        rels.add_relationship(reltype='http://rt-image', target=part,
                              rId='rId2')
        return rels

    @pytest.fixture
    def rels_elm(self, request):
        """
        Return a rels_elm mock that will be returned from
        CT_Relationships.new()
        """
        # create rels_elm mock with a .xml property
        rels_elm = Mock(name='rels_elm')
        xml = PropertyMock(name='xml')
        type(rels_elm).xml = xml
        rels_elm.attach_mock(xml, 'xml')
        rels_elm.reset_mock()  # to clear attach_mock call
        # patch CT_Relationships to return that rels_elm
        patch_ = patch.object(CT_Relationships, 'new', return_value=rels_elm)
        patch_.start()
        request.addfinalizer(patch_.stop)
        return rels_elm

    @pytest.fixture
    def reltype(self):
        return 'http://rel/type'

    @pytest.fixture
    def url(self):
        return 'https://github.com/scanny/python-pptx'


class DescribeUnmarshaller(object):

    def it_can_unmarshal_from_a_pkg_reader(
            self, pkg_reader_, pkg_, part_factory_, _unmarshal_parts,
            _unmarshal_relationships, parts_dict_):
        # exercise ---------------------
        Unmarshaller.unmarshal(pkg_reader_, pkg_, part_factory_)
        # verify -----------------------
        _unmarshal_parts.assert_called_once_with(
            pkg_reader_, pkg_, part_factory_
        )
        _unmarshal_relationships.assert_called_once_with(
            pkg_reader_, pkg_, parts_dict_
        )
        for part in parts_dict_.values():
            part.after_unmarshal.assert_called_once_with()
        pkg_.after_unmarshal.assert_called_once_with()

    def it_can_unmarshal_parts(
            self, pkg_reader_, pkg_, part_factory_, parts_dict_, partnames_,
            content_types_, blobs_):
        # fixture ----------------------
        partname_, partname_2_ = partnames_
        content_type_, content_type_2_ = content_types_
        blob_, blob_2_ = blobs_
        # exercise ---------------------
        parts = Unmarshaller._unmarshal_parts(
            pkg_reader_, pkg_, part_factory_
        )
        # verify -----------------------
        assert (
            part_factory_.call_args_list == [
                call(partname_, content_type_, blob_, pkg_),
                call(partname_2_, content_type_2_, blob_2_, pkg_)
            ]
        )
        assert parts == parts_dict_

    def it_can_unmarshal_relationships(self):
        # test data --------------------
        reltype = 'http://reltype'
        # mockery ----------------------
        pkg_reader = Mock(name='pkg_reader')
        pkg_reader.iter_srels.return_value = (
            ('/',         Mock(name='srel1', rId='rId1', reltype=reltype,
             target_partname='partname1', is_external=False)),
            ('/',         Mock(name='srel2', rId='rId2', reltype=reltype,
             target_ref='target_ref_1',   is_external=True)),
            ('partname1', Mock(name='srel3', rId='rId3', reltype=reltype,
             target_partname='partname2', is_external=False)),
            ('partname2', Mock(name='srel4', rId='rId4', reltype=reltype,
             target_ref='target_ref_2',   is_external=True)),
        )
        pkg = Mock(name='pkg')
        parts = {}
        for num in range(1, 3):
            name = 'part%d' % num
            part = Mock(name=name)
            parts['partname%d' % num] = part
            pkg.attach_mock(part, name)
        # exercise ---------------------
        Unmarshaller._unmarshal_relationships(pkg_reader, pkg, parts)
        # verify -----------------------
        expected_pkg_calls = [
            call.load_rel(reltype, parts['partname1'], 'rId1', False),
            call.load_rel(reltype, 'target_ref_1', 'rId2', True),
            call.part1.load_rel(reltype, parts['partname2'], 'rId3', False),
            call.part2.load_rel(reltype, 'target_ref_2', 'rId4', True),
        ]
        assert pkg.mock_calls == expected_pkg_calls

    # fixtures ---------------------------------------------

    @pytest.fixture
    def blobs_(self, request):
        blob_ = loose_mock(request, spec=str, name='blob_')
        blob_2_ = loose_mock(request, spec=str, name='blob_2_')
        return blob_, blob_2_

    @pytest.fixture
    def content_types_(self, request):
        content_type_ = loose_mock(request, spec=str, name='content_type_')
        content_type_2_ = loose_mock(request, spec=str, name='content_type_2_')
        return content_type_, content_type_2_

    @pytest.fixture
    def part_factory_(self, request, parts_):
        part_factory_ = loose_mock(request, spec=Part)
        part_factory_.side_effect = parts_
        return part_factory_

    @pytest.fixture
    def partnames_(self, request):
        partname_ = loose_mock(request, spec=str, name='partname_')
        partname_2_ = loose_mock(request, spec=str, name='partname_2_')
        return partname_, partname_2_

    @pytest.fixture
    def parts_(self, request):
        part_ = instance_mock(request, Part, name='part_')
        part_2_ = instance_mock(request, Part, name='part_2')
        return part_, part_2_

    @pytest.fixture
    def parts_dict_(self, request, partnames_, parts_):
        partname_, partname_2_ = partnames_
        part_, part_2_ = parts_
        return {partname_: part_, partname_2_: part_2_}

    @pytest.fixture
    def pkg_(self, request):
        return instance_mock(request, Package)

    @pytest.fixture
    def pkg_reader_(self, request, partnames_, content_types_, blobs_):
        partname_, partname_2_ = partnames_
        content_type_, content_type_2_ = content_types_
        blob_, blob_2_ = blobs_
        spart_return_values = (
            (partname_, content_type_, blob_),
            (partname_2_, content_type_2_, blob_2_),
        )
        pkg_reader_ = instance_mock(request, PackageReader)
        pkg_reader_.iter_sparts.return_value = spart_return_values
        return pkg_reader_

    @pytest.fixture
    def _unmarshal_parts(self, request, parts_dict_):
        return method_mock(
            request, Unmarshaller, '_unmarshal_parts',
            return_value=parts_dict_
        )

    @pytest.fixture
    def _unmarshal_relationships(self, request):
        return method_mock(request, Unmarshaller, '_unmarshal_relationships')


# from ..unitutil import (
#     absjoin, class_mock, cls_attr_mock, instance_mock, loose_mock,
#     method_mock, test_file_dir
# )
# test_pptx_path = absjoin(test_file_dir, 'test.pptx')
# dir_pkg_path = absjoin(test_file_dir, 'expanded_pptx')
# zip_pkg_path = test_pptx_path

# def test_it_finds_default_case_insensitive(self, cti):
#     """_ContentTypesItem[partname] finds default case insensitive"""
#     # setup ------------------------
#     partname = '/ppt/media/image1.JPG'
#     content_type = 'image/jpeg'
#     cti._defaults = {'jpg': content_type}
#     # exercise ---------------------
#     val = cti[partname]
#     # verify -----------------------
#     assert val == content_type

# def test_it_finds_override_case_insensitive(self, cti):
#     """_ContentTypesItem[partname] finds override case insensitive"""
#     # setup ------------------------
#     partname = '/foo/bar.xml'
#     case_mangled_partname = '/FoO/bAr.XML'
#     content_type = 'application/vnd.content_type'
#     cti._overrides = {
#         partname: content_type
#     }
#     # exercise ---------------------
#     val = cti[case_mangled_partname]
#     # verify -----------------------
#     assert val == content_type

# def test_save_accepts_stream(self, tmp_pptx_path):
#     pkg = Package().open(dir_pkg_path)
#     stream = StringIO()
#     # exercise --------------------
#     pkg.save(stream)
#     # verify ----------------------
#     # can't use is_zipfile() directly on stream in Python 2.6
#     stream.seek(0)
#     with open(tmp_pptx_path, 'wb') as f:
#         f.write(stream.read())
#     msg = "Package.save(stream) did not create zipfile"
#     assert is_zipfile(tmp_pptx_path), msg


# @pytest.fixture
# def tmp_pptx_path(tmpdir):
#     return str(tmpdir.join('test_python-pptx.pptx'))
